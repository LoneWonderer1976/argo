"""login.py -- the ONE interactive step: log into Garmin Connect once, on Ben's PC.

    python -m argo.login

Asks for the account's email and password (and the MFA code if the account has one), then:
  1. caches the tokens in .garmin_tokens/ (git-ignored) so `python -m argo.sync` works locally, and
  2. prints the token string to paste into the GitHub repository secret GARMINTOKENS, which is
     what the hourly Action logs in with.

Ben types the credentials; nothing stores them. The tokens last about a year -- when the Action
starts failing with an authentication error, run this again and replace the secret.
"""
import getpass
import sys

from .sync import TOKEN_DIR


def main() -> None:
    try:
        from garminconnect import Garmin
    except ImportError:
        sys.exit("garminconnect is not installed:  pip install garminconnect")
    print("Garmin Connect login for Argo (the account the watch syncs to)")
    email = input("  email: ").strip()
    password = getpass.getpass("  password (hidden): ")
    api = Garmin(email, password, prompt_mfa=lambda: input("  MFA code: ").strip())
    TOKEN_DIR.mkdir(exist_ok=True)
    api.login(str(TOKEN_DIR))
    name = api.get_full_name() if hasattr(api, "get_full_name") else "?"
    tokens = api.client.dumps()
    print(f"\nlogged in as {name}; tokens cached in {TOKEN_DIR}\n")
    print("Paste EVERYTHING between the lines into the repository secret GARMINTOKENS")
    print("(GitHub -> the argo repo -> Settings -> Secrets and variables -> Actions -> New secret):")
    print("-" * 78)
    print(tokens)
    print("-" * 78)


if __name__ == "__main__":
    main()
