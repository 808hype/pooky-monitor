import requests
from bs4 import BeautifulSoup
import proxyscrape
import time
import datetime
import json

collector = proxyscrape.create_collector("supreme", "http")
collector.apply_filter({'type': 'http'})


def read_file():
    with open('config.json') as config:
        data = json.load(config)
        discord_webhook = data["discordWebhook"]
        slack_webhook = data["slackWebhook"]
        region = data["region"]
        delay = data["delay"]
        use_proxies = data["useProxies"]
        proxies = data["proxies"]
    return discord_webhook, slack_webhook, region, delay, use_proxies, proxies


def parse_html(html):
    timestamp = datetime.datetime.now().isoformat()
    tohru = None
    soup = BeautifulSoup(html, "html.parser")
    if "us" in soup.body["class"]:
        region = "US"
    elif "eu" in soup.body["class"]:
        region = "EU"
    else:
        region = "JP"
    pooky_scripts = soup.find("script", "src")
    if not pooky_scripts:
        return None
    else:
        print("Pooky detected!")
        pooky = "https://www.supremenewyork.com" + pooky_scripts["src"][1:]
    tohru_scripts = soup.find_all("script", type="text/javascript")
    for script in tohru_scripts:
        if "supremetohru" in script:
            tohru = script
            tohru = tohru.split(" = ")[1].replace("</script>", "")
            tohru = tohru.replace("\"", "")
            tohru = tohru.replace(";", "")
    return pooky, tohru, region, timestamp


def send_webhook(discordWebhook, slackWebhook, pooky, tohru, region, timestamp):
    headers = {"Content-Type": "application/json"}
    if tohru is None:
        tohru = "Unknown"
    if not discordWebhook == "":
        payload = {"embed": {"title": "[New Pooky Detected!](" + pooky + ")", "color": 3553599, "timestamp": timestamp, "fields": [{"name": "Region", "value": region}, {"name": "Tohru", "value": tohru}]}}
        r = requests.post(discordWebhook, headers=headers, json=payload)
        discord_status = str(r.status_code)
    else:
        discord_status = "N/A"
    if not slackWebhook == "":
        payload = [{"type": "section", "text": {"type": "mrkdwn", "text": "<" + pooky + "|New Pooky Detected!>"}}, {"type": "divider"}, {"type": "section", "fields": [{"type": "mrkdwn", "text": "*Region*\n" + region}, {"type": "mrkdwn", "text": "*Tohru*\n" + tohru}]}]
        r = requests.post(slackWebhook, headers=headers, json=payload)
        slack_status = str(r.status_code)
    else:
        slack_status = "N/A"
    return discord_status, slack_status


def monitor_pooky(data):
    user_agent = "Mozilla/5.0 (iPhone; CPU iPhone OS 12_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/12.1 Mobile/15E148 Safari/604.1"
    headers = {"user-agent": user_agent}
    if not data[4]:
        while True:
            if data[2].upper() == "US":
                code = "us"
            elif data[2].upper() == "EU":
                code = "uk"
            else:
                code = "jp"
            proxy_info = collector.get_proxy({'code': code, 'type': 'http'})
            print("Monitoring...")
            if proxy_info is None:
                print("Unable to scrape proxies!")
                r = requests.get("https://www.supremenewyork.com/mobile", headers=headers)
            else:
                proxies = {"http": proxy_info[0] + ":" + proxy_info[1]}
                r = requests.get("https://www.supremenewyork.com/mobile", headers=headers, proxies=proxies)
            parsed = parse_html(r.text)
            if parsed is None:
                pass
            else:
                hooked = send_webhook(data[0], data[1], parsed[0], parsed[1], parsed[2], parsed[3])
                break
            time.sleep(data[3])
    else:
        proxylist = data[5]
        max_value = len(proxylist) - 1
        rotate_value = 0
        while True:
            proxies = {"http": proxylist[rotate_value]}
            print("Monitoring...")
            r = requests.get("https://supremenewyork.com/mobile", headers=headers, proxies=proxies)
            parsed = parse_html(r.text)
            if parsed[0] is None:
                pass
            else:
                hooked = send_webhook(data[0], data[1], parsed[0], parsed[1], parsed[2], parsed[3])
                break
            if rotate_value < max_value:
                rotate_value += 1
            else:
                rotate_value = 0
            time.sleep(data[3])
    return hooked


print("Reading settings...")
config = read_file()
print("Starting monitor...")
stat = monitor_pooky(config)
print("Discord Status: " + stat[0] + "\nSlack Status: " + stat[1] + "\nRestart the monitor after pooky is disabled.")
