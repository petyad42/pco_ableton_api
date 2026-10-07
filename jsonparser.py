from time import sleep
from xml.etree.ElementTree import tostring

import requests
import simplejson
import json
from dotenv import load_dotenv
import os
import sys
import shutil
import gzip
import progressbar
from unidecode import unidecode
from rich.console import Console
from rich.table import Table


load_dotenv()



#url = "https://api.planningcenteronline.com/services/v2/plans/86631307/items"
#base_url = "https://services.planningcenteronline.com/plans/86631378"

usr_input = input("Please enter service link or press ENTER to use example service: ")
base_url = ""
if usr_input:
    if usr_input.split("//")[0]=="https:":
        base_url = usr_input
    else:
        raise Exception("Invalid URL")
else:
    base_url = "https://services.planningcenteronline.com/plans/91675400"
plan_id = base_url.split("/")[-1]

url = f'https://api.planningcenteronline.com/services/v2/plans/{plan_id}/items'

token = os.getenv("PCO_TOKEN")

headers = {
    'Authorization': token
}

print("Retrieving songs from website...")
response = requests.get(url, headers=headers)
print("Response data has arrived") if response != None else print("There has been an error during the HTTP GET")

full_json = response.json()

filtered_items = [
        item for item in full_json.get("data", []) 
        if item.get("attributes", {}).get("item_type") == "song"
    ]



while full_json.get("links",{}).get("next"):
    url = full_json.get("links",{}).get("next")
    response = requests.get(url, headers=headers)
    full_json = response.json()
    for item in full_json.get("data",[]):
        if item.get("attributes", {}).get("item_type") == "song":
            filtered_items.append(item)
    print("There are more songs in offset API link")


refined_songs = []



for i,item in enumerate(filtered_items):
    attrs = item.get("attributes", {})
    relationships = item.get("relationships", {})
    song_data = relationships.get("song", {}).get("data")
    arr_data = relationships.get("arrangement", {}).get("data")

    song_info = {
        "title": unidecode(attrs.get("title")),
        "key_name": attrs.get("key_name"),
        "song_id": song_data.get("id")if song_data else None,
        "arrangement_id": arr_data.get("id") if arr_data else None
        ,"api_link": f'https://api.planningcenteronline.com/services/v2/songs/{song_data.get("id")}/arrangements/{arr_data.get("id")}'
    }

    refined_songs.append(song_info)


table = Table(title="Songs")
rows=[]
cols=['#','Title','Key','Meter','BPM']

print("Creating table:")
leng = len(refined_songs)
progressbar.printProgressBar(0, leng, prefix = 'Progress:', suffix = 'Complete', length = 50)

for i,song in enumerate(refined_songs):
    api_link = song["api_link"]
    song_response = requests.get(api_link, headers=headers)
    curr_song_json = song_response.json()
    song['bpm'] =curr_song_json.get("data",{}).get("attributes", {}).get("bpm")
    song['meter'] = curr_song_json.get("data",{}).get("attributes", {}).get("meter")
    rows.append([str(i+1),str(song['title']),str(song['key_name']),str(song['meter']),str(song['bpm'])])
    progressbar.printProgressBar(i + 1, leng, prefix = 'Progress:', suffix = 'Complete', length = 50)


for column in cols:
    table.add_column(column)

for row in rows:
    table.add_row(*row, style='bright_green')

console = Console()
console.print(table)


# Here I take the first argument which should be and ALS ableton file and then
# make a duplicate (for safety reasons) then I change the file extension to zip
# and finally unzip it to access the project xml file of the setlist
# NOTE: This was the easiest way around it. The existing libraries are out of date
# and doesn't work proprerly

src_file = sys.argv[1]
cwd = os.getcwd()
source=cwd+"/"+src_file
setlist_xml = "setlist.xml"
destination_xml = cwd+"/"+setlist_xml
destination_als = cwd + "/output.als"


with gzip.open(source, 'rb') as f_in:
    with open(destination_xml, 'wb') as f_out:
        shutil.copyfileobj(f_in, f_out)

import xml.etree.ElementTree as ET

tree = ET.parse("setlist.xml")
root = tree.getroot()
live_set = root.find('LiveSet')

# 1. Get and bump NextPointeeId
next_id_el = live_set.find('NextPointeeId')
new_id = int(next_id_el.get('Value'))
next_id_el.set('Value', str(new_id + len(refined_songs)))

# 2. Add the new Scene
scenes_el = live_set.find('Scenes')
for i,song in enumerate(refined_songs):
    scene_id = new_id + i
    new_scene = ET.fromstring(f"""<Scene Id="{scene_id}">
        <FollowAction>
            <FollowTime Value="4" />
            <IsLinked Value="true" />
            <LoopIterations Value="1" />
            <FollowActionA Value="4" />
            <FollowActionB Value="0" />
            <FollowChanceA Value="100" />
            <FollowChanceB Value="0" />
            <JumpIndexA Value="0" />
            <JumpIndexB Value="0" />
            <FollowActionEnabled Value="false" />
        </FollowAction>
        <Name Value="{song['title']}" />
        <Annotation Value="" />
        <Color Value="-1" />
        <Tempo Value="{song['bpm'] if song['bpm'] else 404}"/>
        <IsTempoEnabled Value="true" />
        <TimeSignatureId Value="{(198 if song['meter'].split('/')[-1] == "4" else 297)if song['meter'] else 198}" />
        <IsTimeSignatureEnabled Value="true" />
        <LomId Value="0" />
        <ClipSlotsListWrapper LomId="0" />
    </Scene>""")
    scenes_el.append(new_scene)
#    print(f"{song['title']}: {('4/' if song['meter'].split('/')[-1]=='4' else '6/') if song['meter'] else ''}{song['meter'].split('/')[-1] if song['meter'] else 'nope'}")


# 3. *** THE CRITICAL PART ***
# Add a matching blank ClipSlot to every track's ClipSlotList
    blank_slot = f"""<ClipSlot Id="{scene_id}">
        <LomId Value="0" />
        <ClipSlot>
            <Value />
        </ClipSlot>
        <HasStop Value="true" />
        <NeedRefreeze Value="true" />
    </ClipSlot>"""

# Step 3 - CORRECTED: update ALL ClipSlotLists in every track, not just the first
    for tag in ('MidiTrack', 'AudioTrack', 'GroupTrack', 'ReturnTrack'):
        for track in live_set.find('Tracks').findall(tag):
            for clip_slot_list in track.findall('.//ClipSlotList'):  # findall, not find
                # Only add slots to lists that already have slots
                # (ReturnTrack FreezeSequencer stays empty, MidiTrack both lists get updated)
                if len(clip_slot_list) > 0:
                    clip_slot_list.append(ET.fromstring(blank_slot))

ET.indent(tree, space='\t')  # optional, only Python 3.9+

xml_bytes = ET.tostring(root, encoding='unicode', xml_declaration=False)
xml_output = '<?xml version="1.0" encoding="UTF-8"?>\n' + xml_bytes
with open("setlist_modified.xml", 'w', encoding='utf-8') as f:
    f.write(xml_output)

try:
    with open("setlist_modified.xml", 'rb') as f_in:
        with gzip.open(destination_als, 'wb') as f_out:
            shutil.copyfileobj(f_in, f_out)
        print(f"Success! Found {len(filtered_items)} songs and saved them to output.als.")
except Exception as e:
    print(e)

# Put file name here if it needs to be deleted after the script runs
files_to_delete = ["setlist.xml","setlist_modified.xml"]

for f in files_to_delete:
    os.remove(f)