#!/usr/bin/python3

import requests, json, re, random, csv, time, argparse, os, sys, urllib3
from bs4 import BeautifulSoup
from termcolor import colored
from datetime import date, datetime

class EmailScraper():

    def __init__(self):
        self.count = 0
        self.depth = 3
        self.employee_names = []
        self.employee_titles = []
        self.employee_emails = []
        self.proxy_address = ""
        self.user_agent = {"User-Agent": "Mozilla/5.0 (Android 4.4; Mobile; rv:41.0) Gecko/41.0 Firefox/41.0"}

    def proxy(self, proxy):
        if proxy:
            address = proxy.split("/")[2]
            if "https" in proxy:
                print(address)
                self.proxy_address = {"https": address}
            else:
                print(address)
                self.proxy_address = {"http": address} 

    def search_google_linkedin(self, comp):
        fullDomain = comp
        if "." in comp:
            comp = comp.split(".")[0]
        page = f"{self.depth}0"
        page_count = 1
        print(f"\nSearching Google - {self.depth} page(s) deep...")
        for i in range(0,int(page),10):
            url = 'https://www.google.com/search?q=site%3Alinkedin.com+works+at+' + comp + '&start=' + str(i)
            url2 = 'https://www.google.com/search?q=site%3Alinkedin.com+works+at+' + fullDomain + '&start=' + str(i)
            print(f"Searching page {page_count} of {self.depth}...")
            page_count += 1
            res = requests.get(url, headers=self.user_agent, proxies=self.proxy_address, verify=False)
            res1 = requests.get(url2, headers=self.user_agent, proxies=self.proxy_address, verify=False)
            if res.status_code and res1.status_code == 200:
                self.find_names(res.text)
                self.find_names(res1.text)
            elif res.status_code == 429:
                print("\nGoogle is on to our IP!")
                print("-"*70 + "\n")
                print("RESULTS:")
                for email in self.employee_emails:
                    print(email)
                total = len(self.employee_emails)
                if total == 0:
                    print(f"\nFound {total} employees... *Suspicious*\n[!] Possibly Google is on to us! [!]\n")
                else:
                    print(f"\nFound {total} employees...")
                    sys.exit()
                time.sleep(2.5)

    def search_hunter(self, comp, api):
        url_account_data = f"https://api.hunter.io/v2/account?api_key={api}"
        account_info = requests.get(url_account_data, proxies=self.proxy_address, verify=False)
        account_info = json.loads(account_info.text)
        print(f"Plan Type: {account_info['data']['plan_name']}")
        print(f"Balance: {account_info['data']['calls']['used']} Out of {account_info['data']['calls']['available']}")
        print(f"Requests: {account_info['data']['requests']['searches']['used']} Out of {account_info['data']['requests']['searches']['available']}")
        print(f"Verifications: {account_info['data']['requests']['verifications']['used']} Out of {account_info['data']['requests']['verifications']['available']}")

        url = f"https://api.hunter.io/v2/domain-search?domain={comp}&api_key={api}"
        print(f"\nSearching Hunter.io...")
        res = requests.get(url, proxies=self.proxy_address, verify=False)
        if res.status_code == 429:
            print("\n[!] You have reached your usage limit for Hunter.io [!]\n")
            sys.exit()
        data = json.loads(res.text)
                
        # Get email pattern
        if data['data']['pattern']:
            emailPattern = data['data']['pattern'].replace('{', '').replace('}', '').title()
            if emailPattern == "Flast":
                print(f"\n[+] Pattern Found: FirstNameInitialLastName (JDoe@{comp})\n")
            elif emailPattern == "First.Last":
                print(f"\n[+] Pattern Found: FirstName.LastName (John.Doe@{comp})\n")
            elif emailPattern == "Lastf":
                print(f"\n[+] Pattern Found: LastNameFirstNameInitial (DoeJ@{comp})\n")
            elif emailPattern == "Firstl":
                print(f"\n[+] Pattern Found: FirstNameLastNameInitial (JohnD@{comp})\n")
            elif emailPattern == "First":
                print(f"\n[+] Pattern Found: FirstName (John@{comp})\n")
        else:
            pass

        # Get details and parse
        hunter_fn = [firstn['first_name'] for firstn in data['data']['emails']]
        hunter_ln = [lastn['last_name'] for lastn in data['data']['emails']]
        hunter_emails = [emails['value'] for emails in data['data']['emails']]
        hunter_position = [pos['position'] for pos in data['data']['emails']]

        for firstName, lastName, emails, title in zip(hunter_fn, hunter_ln, hunter_emails, hunter_position):
            print(f"{firstName} {lastName} - {title} - {emails}")

        time.sleep(1)
        if hunter_emails:
            for hemail in hunter_emails:
                if hemail not in self.employee_emails:
                    self.employee_emails.append(hemail)

        print("\n" + "-"*20 + " END OF Hunter.io RESULTS " + "-"*20)
	
    def find_names(self, html):
        try:
            soup = BeautifulSoup(html, "xml")
            # print(soup) # Just print soup and find someones name, then get the span class name before it.
            # It might be that the value of this class changes, check in your browsers Inspect window for the class value which is around their names.
            match = soup.findAll("span", {"class":"CVA68e qXLe6d fuLhoc ZWRArf"})
            for m in match:
                m = m.text
                if m.count("-") >= 2:
                    details = m.split("-")
                    names = details[0].strip()
                    titles = details[1].strip()
                    self.employee_titles.append(titles)
                    self.employee_names.append(names)
        except:
            print("\n[!] Something went wrong grabbing names. [!]")
                
    def email_mangler(self, emailformat):
        # Mange emails out of names and format provided
        names = self.employee_names
        #print(names)
        for name in names:
            #print(name)
            fn = name.split(" ")[0]
            #print(fn)
            fi = fn[0]
            ln = name.split(" ")[1]
            li = ln[0]          
            email = emailformat.replace("<fn>", fn).replace("<fi>", fi).replace("<ln>", ln).replace("<li>", li).lower()
            if email not in self.employee_emails:
                self.employee_emails.append(email)
        
    def run(self):
        # Run the main program
        parser = argparse.ArgumentParser()
        parser.add_argument('-c', '--company', help='Provide the domain name (domain.com)', required=True)
        parser.add_argument('-e', '--email', help='"<fi>.<ln>@domain.com" OR "<fn>.<ln>@domain.com"', required=False)
        parser.add_argument('-d', '--depth', help='Search results page depth (default 3)', type=int, required=False, default=3)
        parser.add_argument("-p", "--proxy", help="http(s)://localhost:8080", default='')
        parser.add_argument("-ha", "--hunterapi", help="Provide an API for Hunter.io", required=False)
        args = parser.parse_args()
        
        if args.proxy:
            self.proxy(args.proxy)
        
        if args.hunterapi:
            self.search_hunter(args.company, args.hunterapi)

        if args.company and args.email:
            self.depth = args.depth
            self.search_google_linkedin(args.company)
            self.email_mangler(args.email)
            print("-"*70 + "\n")
            print("RESULTS:")
            for email in self.employee_emails:
                print(email)
            total = len(self.employee_emails)
            if total == 0:
                print(f"\nFound {total} employees... *Suspicious*\n[!] Possibly Google is on to us! [!]\n")
            else:
                print(f"\nFound {total} employees...")
            
        else:
            print("\n[?] Maybe run with '-ha' Hunter.io first and then use '-e' and the email format [?]\n")
            
if __name__ == "__main__":
    urllib3.disable_warnings()
    x = EmailScraper()
    x.run()
