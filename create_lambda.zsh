#!/usr/bin/zsh

EXCLUDE_LIST=(
  ".git/*"
  ".*_cache/*"
  ".terraform/*"
  ".venv/*"
  "htmlcov/*"
  "python/*"
  ".coverage"
  ".env"
  "lambda.zip"
  "terraform.tfstate"
  "terraform.tfstate.backup"
  "terraform.tfvars"
)

EXCLUDE_ARGS=()
for item in "${EXCLUDE_LIST[@]}"; do
  EXCLUDE_ARGS+=("--exclude=$item")
done

zip -r "lambda.zip" . "${EXCLUDE_ARGS[@]}"
