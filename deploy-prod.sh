#!/bin/bash

FILE="template.yaml"

# Check if the file exists
if [[ -f "$FILE" ]]; then
    echo "$FILE exists. Deleting..."
    rm -f "$FILE"
else
    echo "$FILE does not exist."
fi

cp template-prod.yaml template.yaml

# Copy recurring files
rsync -av functions/layers/ functions/ocr/ --exclude=requirements.txt
rsync -av functions/layers/ functions/prompts_ner/ --exclude=requirements.txt

sam validate --region us-east-2
sam build -c -p --use-container
sam deploy \
--profile docudive \
--stack-name docudive-backend-prod \
--region us-east-2 \
--no-confirm-changeset \
--capabilities CAPABILITY_IAM CAPABILITY_AUTO_EXPAND \
--on-failure ROLLBACK \
--resolve-s3 \
--image-repository 456657096993.dkr.ecr.us-east-2.amazonaws.com/docudive-prod