"""Optional cloud sync client (standard library only). Uploads and downloads case archives, which are
already ciphertext, through the AWS API defined in infra/. The cloud never sees a passphrase or plaintext.
Sign-in tokens live in memory only and are never written to disk."""
import json
import os
import re
import shutil
import time
import urllib.error
import urllib.parse
import urllib.request

API_TIMEOUT, TRANSFER_TIMEOUT = 30, 900
LOOPBACK = ("127.0.0.1", "localhost", "::1")
CASE_ID = re.compile(r"[0-9a-f]{16}")
FRIENDLY = {  # Cognito error types -> what the advocate should read
    "NotAuthorizedException": "Wrong username or password, or the session has expired.",
    "UserNotFoundException": "Wrong username or password, or the session has expired.",
    "CodeMismatchException": "That code is wrong. Check your authenticator app and try again.",
    "ExpiredCodeException": "That code has expired. Try the next one.",
    "TooManyRequestsException": "Too many attempts. Wait a few minutes and try again.",
    "LimitExceededException": "Too many attempts. Wait a few minutes and try again.",
    "PasswordResetRequiredException": "Your password must be reset. Ask your administrator.",
    "UserNotConfirmedException": "This account is not confirmed. Ask your administrator.",
}


class CloudError(Exception):
    def __init__(self, message, status=502):
        super().__init__(message)
        self.status = status


def _https(url, what):
    u = urllib.parse.urlparse(url)
    if not (u.scheme == "https" or (u.scheme == "http" and u.hostname in LOOPBACK)) or not u.hostname:
        raise CloudError(f"{what} must be an https address", 400)  # never send tokens or data in the clear
    return url


def check_config(cfg):
    cfg = {k: str(cfg.get(k, "")).strip() for k in ("api_url", "region", "client_id")}
    if not re.fullmatch(r"[a-z]{2}(-[a-z]+)+-\d", cfg["region"]):
        raise CloudError("region looks wrong, e.g. ap-south-1", 422)
    if not re.fullmatch(r"[\w]{10,64}", cfg["client_id"]):
        raise CloudError("client id looks wrong", 422)
    cfg["api_url"] = _https(cfg["api_url"], "the API address").rstrip("/")
    return cfg


def _request(req, timeout):
    try:
        return urllib.request.urlopen(req, timeout=timeout)
    except urllib.error.HTTPError as e:
        raise e
    except (urllib.error.URLError, TimeoutError, OSError):
        raise CloudError("Cannot reach AWS. Check your internet connection.", 503)


class Cloud:
    def __init__(self, cfg, cognito_endpoint=None):
        self.cfg = check_config(cfg)
        self.cognito = cognito_endpoint or f"https://cognito-idp.{self.cfg['region']}.amazonaws.com/"
        _https(self.cognito, "the sign-in address")
        self.id_token = self.refresh_token = self.username = None
        self.expires = 0.0
        self.pending = None

    @property
    def signed_in(self):
        return bool(self.id_token)

    # ---- sign-in (Cognito user pool, JSON API) ----
    def _cognito(self, target, payload):
        req = urllib.request.Request(
            self.cognito, json.dumps(payload).encode(), method="POST",
            headers={"X-Amz-Target": f"AWSCognitoIdentityProviderService.{target}",
                     "Content-Type": "application/x-amz-json-1.1"})
        try:
            with _request(req, API_TIMEOUT) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            kind = (json.loads(e.read() or b"{}").get("__type") or "").split("#")[-1]
            raise CloudError(FRIENDLY.get(kind, f"Sign-in failed ({kind or e.code})."), 401 if e.code in (400, 401) else 502)

    def login(self, username, password):
        """Returns {"state": "ok"}, {"state": "mfa"}, or {"state": "mfa_setup", "secret", "uri"}."""
        self.sign_out()
        r = self._cognito("InitiateAuth", {"AuthFlow": "USER_PASSWORD_AUTH", "ClientId": self.cfg["client_id"],
                                           "AuthParameters": {"USERNAME": username, "PASSWORD": password}})
        return self._after_auth(r, username)

    def _after_auth(self, r, username):
        if "AuthenticationResult" in r:
            a = r["AuthenticationResult"]
            self.id_token, self.username, self.pending = a["IdToken"], username, None
            self.refresh_token = a.get("RefreshToken", self.refresh_token)
            self.expires = time.time() + int(a.get("ExpiresIn", 3600))
            return {"state": "ok"}
        ch = r.get("ChallengeName")
        if ch == "SOFTWARE_TOKEN_MFA":
            self.pending = {"challenge": ch, "session": r["Session"], "username": username}
            return {"state": "mfa"}
        if ch == "MFA_SETUP":  # first sign-in: enrol an authenticator app
            a = self._cognito("AssociateSoftwareToken", {"Session": r["Session"]})
            self.pending = {"challenge": ch, "session": a["Session"], "username": username}
            secret = a["SecretCode"]
            return {"state": "mfa_setup", "secret": secret,
                    "uri": f"otpauth://totp/NyayaAI:{urllib.parse.quote(username)}?secret={secret}&issuer=NyayaAI"}
        if ch == "NEW_PASSWORD_REQUIRED":
            raise CloudError("This account needs a permanent password. Ask your administrator to set one.", 401)
        raise CloudError(f"Unsupported sign-in step ({ch}).", 501)

    def submit_code(self, code):
        p = self.pending
        if not p:
            raise CloudError("Sign in first.", 409)
        code, user = code.strip(), p["username"]
        if p["challenge"] == "MFA_SETUP":
            v = self._cognito("VerifySoftwareToken", {"Session": p["session"], "UserCode": code})
            if v.get("Status") != "SUCCESS":
                raise CloudError(FRIENDLY["CodeMismatchException"], 401)
            r = self._cognito("RespondToAuthChallenge", {
                "ClientId": self.cfg["client_id"], "ChallengeName": "MFA_SETUP", "Session": v["Session"],
                "ChallengeResponses": {"USERNAME": user}})
        else:
            r = self._cognito("RespondToAuthChallenge", {
                "ClientId": self.cfg["client_id"], "ChallengeName": "SOFTWARE_TOKEN_MFA", "Session": p["session"],
                "ChallengeResponses": {"USERNAME": user, "SOFTWARE_TOKEN_MFA_CODE": code}})
        return self._after_auth(r, user)

    def sign_out(self):
        self.id_token = self.refresh_token = self.pending = None
        self.expires = 0.0

    def _token(self):
        if not self.id_token:
            raise CloudError("Sign in to the cloud first.", 401)
        if time.time() > self.expires - 60:
            try:
                r = self._cognito("InitiateAuth", {"AuthFlow": "REFRESH_TOKEN_AUTH", "ClientId": self.cfg["client_id"],
                                                   "AuthParameters": {"REFRESH_TOKEN": self.refresh_token}})
                self._after_auth(r, self.username)
            except CloudError:
                self.sign_out()
                raise CloudError("Cloud session expired. Sign in again.", 401)
        return self.id_token

    # ---- case archive API ----
    def _api(self, method, path, body=None):
        req = urllib.request.Request(
            self.cfg["api_url"] + path, None if body is None else json.dumps(body).encode(), method=method,
            headers={"Authorization": f"Bearer {self._token()}", "Content-Type": "application/json"})
        try:
            with _request(req, API_TIMEOUT) as r:
                return json.loads(r.read() or b"{}")
        except urllib.error.HTTPError as e:
            try:
                detail = json.loads(e.read() or b"{}").get("message")
            except ValueError:
                detail = None
            if e.code == 401:
                self.sign_out()
                raise CloudError("Cloud session expired. Sign in again.", 401)
            raise CloudError(detail or f"The cloud refused the request ({e.code}).", e.code)

    def list_cases(self):
        return self._api("GET", "/cases")

    def push(self, case_id, archive, base_version):
        """Upload an archive file as the next version. Returns the new version number.
        Raises CloudError(409) if someone else pushed since base_version."""
        self._valid(case_id)
        size = os.path.getsize(archive)
        r = self._api("POST", f"/cases/{case_id}/push", {"base_version": base_version, "size": size})
        with open(archive, "rb") as f:
            req = urllib.request.Request(_https(r["url"], "the upload address"), f, method="PUT",
                                         headers={"Content-Length": str(size), "Content-Type": "application/octet-stream"})
            try:
                _request(req, TRANSFER_TIMEOUT).close()
            except urllib.error.HTTPError as e:
                raise CloudError(f"Upload failed ({e.code}).", 502)
        return self._api("POST", f"/cases/{case_id}/commit", {"version": r["version"]})["version"]

    def pull(self, case_id, dest, version=None):
        """Download an archive to the file dest. Returns its version number."""
        self._valid(case_id)
        r = self._api("GET", f"/cases/{case_id}/pull" + (f"?version={int(version)}" if version else ""))
        try:
            with _request(urllib.request.Request(_https(r["url"], "the download address")), TRANSFER_TIMEOUT) as src, \
                    open(dest, "wb") as out:
                shutil.copyfileobj(src, out)
        except urllib.error.HTTPError as e:
            raise CloudError(f"Download failed ({e.code}).", 502)
        return r["version"]

    def delete(self, case_id):
        self._valid(case_id)
        self._api("DELETE", f"/cases/{case_id}")

    @staticmethod
    def _valid(case_id):
        if not CASE_ID.fullmatch(case_id):
            raise CloudError("bad case id", 400)
