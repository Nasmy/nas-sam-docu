import json

block_list = "disposable_email_blocklist.conf"
allow_list = "allowlist.conf"
full_list = "email_list.json"

full_dict = {}
with open(block_list, "r") as file:
    for each in file.readlines():
        full_dict[each.strip()] = False

with open(allow_list, "r") as file:
    for each in file.readlines():
        full_dict[each.strip()] = True

with open(full_list, "w+") as file:
    file.write(json.dumps(full_dict))

print("Done")
