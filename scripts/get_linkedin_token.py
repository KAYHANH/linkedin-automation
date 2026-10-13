"""Interactive helper to obtain LinkedIn Access Token and Author Member URN."""

import sys
import urllib.parse
import httpx


def main():
    print("=" * 60)
    print("LINKEDIN OAUTH TOKEN & MEMBER URN HELPER")
    print("=" * 60)

    client_id = input("Enter your LinkedIn Client ID: ").strip()
    if not client_id:
        print("[ERROR] Client ID cannot be empty.")
        return 1

    client_secret = input("Enter your LinkedIn Client Secret: ").strip()
    if not client_secret:
        print("[ERROR] Client Secret cannot be empty.")
        return 1

    redirect_uri = "http://localhost:8000/callback"
    scope = "w_member_social openid profile"
    params = {
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "scope": scope,
    }
    auth_url = f"https://www.linkedin.com/oauth/v2/authorization?{urllib.parse.urlencode(params)}"

    print("\n" + "-" * 60)
    print("STEP 1: Open the following URL in your web browser:")
    print("-" * 60)
    print(auth_url)
    print("-" * 60)
    print("1. Click 'Allow' when LinkedIn prompts for permissions.")
    print("2. Your browser will redirect to a URL starting with:")
    print("   http://localhost:8000/callback?code=...")
    print("   (Even if the browser says 'This site can't be reached', that is normal!)")
    print("3. Copy the ENTIRE URL from your browser's address bar.\n")

    redirected_url = input("Paste the entire redirected URL here: ").strip()

    # Extract 'code' parameter
    parsed = urllib.parse.urlparse(redirected_url)
    qs = urllib.parse.parse_qs(parsed.query)

    if "error" in qs:
        print(f"\n[ERROR] LinkedIn authorization returned an error: {qs.get('error', [''])[0]}")
        print(f"Description: {qs.get('error_description', [''])[0]}")
        return 1

    auth_code = qs.get("code", [None])[0]
    if not auth_code:
        # User might have pasted just the code
        auth_code = redirected_url

    print("\nSTEP 2: Exchanging authorization code for 60-day Access Token...")

    token_url = "https://www.linkedin.com/oauth/v2/accessToken"
    token_data = {
        "grant_type": "authorization_code",
        "code": auth_code,
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": redirect_uri,
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}

    with httpx.Client(timeout=20.0) as client:
        resp = client.post(token_url, data=token_data, headers=headers)
        if resp.status_code != 200:
            print(f"\n[ERROR] Failed to obtain token: HTTP {resp.status_code}")
            print(resp.text)
            return 1

        token_json = resp.json()
        access_token = token_json.get("access_token")
        expires_in = token_json.get("expires_in", 5184000)  # ~60 days

        print(f"[SUCCESS] Access Token generated! (Valid for {expires_in // 86400} days)")

        # STEP 3: Retrieve Member URN
        print("\nSTEP 3: Fetching your LinkedIn Member URN...")
        userinfo_headers = {"Authorization": f"Bearer {access_token}"}
        userinfo_resp = client.get("https://api.linkedin.com/v2/userinfo", headers=userinfo_headers)

        author_urn = None
        member_name = "Authenticated Member"
        if userinfo_resp.status_code == 200:
            u_data = userinfo_resp.json()
            sub = u_data.get("sub")
            member_name = u_data.get("name", member_name)
            if sub:
                author_urn = f"urn:li:person:{sub}"
                print(f"[SUCCESS] Found profile for: {member_name}")
                print(f"[SUCCESS] Author URN: {author_urn}")
            else:
                print("[WARNING] Could not find 'sub' in userinfo response.")
        else:
            print(f"[NOTICE] /v2/userinfo returned HTTP {userinfo_resp.status_code}.")
            print("If OpenID Connect wasn't enabled, you can find your member ID manually.")

        print("\n" + "=" * 60)
        print("YOUR CONFIGURATION CREDENTIALS TO ADD TO .env:")
        print("=" * 60)
        print(f"LINKEDIN_ACCESS_TOKEN={access_token}")
        if author_urn:
            print(f"LINKEDIN_AUTHOR_URN={author_urn}")
        else:
            print("LINKEDIN_AUTHOR_URN=urn:li:person:YOUR_MEMBER_ID")
        print(f"LINKEDIN_CLIENT_ID={client_id}")
        print(f"LINKEDIN_CLIENT_SECRET={client_secret}")
        print("=" * 60)

        # Automatically write/update .env file
        env_path = ".env"
        env_lines = []
        if os.path.exists(env_path):
            with open(env_path, "r", encoding="utf-8") as f:
                env_lines = f.readlines()

        keys_to_set = {
            "LINKEDIN_ACCESS_TOKEN": access_token,
            "LINKEDIN_AUTHOR_URN": author_urn or "urn:li:person:YOUR_MEMBER_ID",
            "LINKEDIN_CLIENT_ID": client_id,
            "LINKEDIN_CLIENT_SECRET": client_secret,
            "LINKEDIN_API_VERSION": "202501",
            "LINKEDIN_ENDPOINT_STYLE": "rest/posts",
            "PUBLISH_TIMEZONE": "Asia/Kolkata",
            "AUTO_PUBLISH": "false",
            "DRY_RUN": "true",
            "GITHUB_STATE_BRANCH": "automation-state",
            "MAX_POST_CHARACTERS": "2200",
            "ENABLE_WEB_SEARCH": "true",
            "LOG_LEVEL": "INFO",
        }

        updated_keys = set()
        new_env_lines = []
        for line in env_lines:
            match = False
            for k, v in keys_to_set.items():
                if line.startswith(f"{k}="):
                    new_env_lines.append(f"{k}={v}\n")
                    updated_keys.add(k)
                    match = True
                    break
            if not match:
                new_env_lines.append(line)

        for k, v in keys_to_set.items():
            if k not in updated_keys:
                new_env_lines.append(f"{k}={v}\n")

        with open(env_path, "w", encoding="utf-8") as f:
            f.writelines(new_env_lines)

        print(f"\n[SAVED] Automatically updated credentials inside '{env_path}'!")
        print("Keep these credentials private and never commit them to git!")

    return 0


if __name__ == "__main__":
    sys.exit(main())
