#!/usr/bin/zsh

DELETE_LIST=(
  "lambda.zip"
  "requirements.zip"
)

for item in "${DELETE_LIST[@]}"; do
  rm -rf "$item"
done
