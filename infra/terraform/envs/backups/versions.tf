terraform {
  required_version = ">= 1.6"
  required_providers {
    cloudflare = {
      source  = "cloudflare/cloudflare"
      version = "~> 5.0"
    }
  }
  # State is LOCAL on the Mini (gitignored) and holds the derived R2 secret key — treat the state
  # file like a credential. Remote state can come with the phase-3 cloud env if/when needed.
}

# Auth comes from the operator's environment — never from git:
#   export CLOUDFLARE_API_TOKEN=...   # bootstrap token; needs "Workers R2 Storage: Edit"
#                                     # + "Account API Tokens: Edit" on the account
provider "cloudflare" {}
