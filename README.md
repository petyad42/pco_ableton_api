# PCO - Ableton API usage
* in the project folder run the following command to enable the **venv**
```
source .venv/bin/activate
```

* Now that you've enabled the venv you can run the script

```
python3 jsonparser.py <ableton_project_file.als>
```

The ```<ableton_project_file.als> ``` ideally should be an empty ableton project.

I've included an empty ableton project to work with, so the default command would be:

```
python3 jsonparser.py ures.als
```
*(üres means empty in Hungarian)*

Then the script will ask for a services online plan link like this:

https://services.planningcenteronline.com/plans/91787528

The website of course requires authentication and access to the organization's plans which is provided by the admin.

The API calls require an Personal Access Token API key which can be requested on the following link: 
https://api.planningcenteronline.com/personal_access_tokens

The API key has to be stored in a ```.env ```  file in the project folder and the the one line should look like this:
```
PCO_TOKEN=Basic <API KEY HERE>
```


If you don't enter a plan link the script will use a default link which has some songs.

When it's finished your terminal should print a table of the songs.

Finally you can find the ```output.als``` file which contains the downloaded songs and its parameters: 
* key
* meter
* BPM