#!/bin/bash

FILE="template.yaml"

# Check if the file exists
if [[ -f "$FILE" ]]; then
    echo "$FILE exists. Deleting..."
    rm -f "$FILE"
else
    echo "$FILE does not exist."
fi

cp template-dev.yaml template.yaml

# Copy recurring files
rsync -av functions/layers/db/ functions/authorizer/db
rsync -av functions/layers/ functions/ocr/ --exclude=requirements.txt
rsync -av functions/layers/ functions/prompts_ner/ --exclude=requirements.txt

sam validate --region us-east-1
sam build -c -p --use-container
sam package --template-file template.yaml --s3-bucket nas-dd-files-digest-bucket --output-template-file packaged.yaml
sam deploy \
--profile nas-docudive \
--template-file packaged.yaml \
--stack-name nas-docudive-backend \
--region us-east-1 \
--no-confirm-changeset \
--capabilities CAPABILITY_IAM CAPABILITY_AUTO_EXPAND \
--on-failure ROLLBACK \
--resolve-s3 \
--image-repository 654654477985.dkr.ecr.us-east-1.amazonaws.com/nas-docudive