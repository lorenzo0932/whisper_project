#!/usr/bin/env bash

#riavvio i container che mi servono rispettivamente per ollama e open-webui e watchtower
docker restart ollama
docker restart open-webui
lms unload --all
#docker restart watchtower
    


