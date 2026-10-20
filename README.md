# Daily: personal hit counter

This Django project includes a small counter for GitHub Pages and personal forms.
Existing todo and meal-planner routes are unchanged.

## API

Create a **Page** in Django admin first, for example:

- Code: `github-home` (case-sensitive, up to 100 letters, digits, `_` or `-`)
- Name: `GitHub home`
- Active: enabled

Only registered, active pages accept hits or expose counts. Codes are public
identifiers, not secrets. Requests use the trailing slashes shown below.

### Log a hit

`POST https://sivashankar.pythonanywhere.com/api/hits/`

Content-Type: `application/json`

```json
{"page": "github-home"}
```

Returns HTTP 201:

```json
{
  "page": "github-home",
  "total_hits": 42,
  "today_hits": 3,
  "date": "2026-10-20",
  "timezone": "UTC",
  "logged_at": "2026-10-20T10:24:00+00:00",
  "location_status": "not_configured"
}
```

Each successful POST records one hit, including repeat visitors, refreshes and
bots. This is **not** a unique-visitor counter. Avoid automatic retries: if a
response is lost after a successful write, retrying may count it twice.
The server records the time and client IP; callers cannot supply these values.

### Read counts without logging

`GET https://sivashankar.pythonanywhere.com/api/hits/github-home/`

Returns HTTP 200 with `page`, `total_hits`, `today_hits`, `date`, and `timezone`
in the same shape as above, without `logged_at` or `location_status`.
An unused registered page returns zero counts. Responses disable caching.
"Today" runs from midnight inclusive to the next midnight exclusive in UTC by
default; event timestamps are stored in UTC.

### Errors

API errors use `{"error": "description"}`:

| Status | Meaning |
| --- | --- |
| 400 | Invalid JSON, page code, IP, extra fields, or preflight headers |
| 403 | Browser origin not allowed |
| 404 | Page not registered or inactive |
| 405 | Wrong HTTP method |
| 413 | POST body exceeds 1,024 bytes |
| 415 | POST Content-Type is not application/json |

Infrastructure/server failures may use Django's standard error responses.
The log endpoint accepts only the `page` field.

## Add to a GitHub Page

Insert this once per page load. Use a different registered code for each page.
The POST already returns counts, so no second request is needed.

```html
<span id="hit-count" aria-live="polite">Loading visits...</span>
<script>
async function recordVisit() {
  const output = document.getElementById("hit-count");
  try {
    const response = await fetch(
      "https://sivashankar.pythonanywhere.com/api/hits/",
      {
        method: "POST",
        credentials: "omit",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ page: "github-home" })
      }
    );
    if (!response.ok) {
      throw new Error(`Counter request failed (${response.status})`);
    }
    const counts = await response.json();
    output.textContent =
      `${counts.total_hits} visits (${counts.today_hits} today)`;
  } catch (error) {
    console.error("Visit counter unavailable:", error);
    output.textContent = "Visit count unavailable";
  }
}
recordVisit();
</script>
```

For a form-submission counter, call the POST once **after a successful form
submission**, instead of on page load. Hosted forms that do not support custom
JavaScript need an integration/webhook or a page you control; placing a URL in
a form description does not execute it.

## Configuration

Configure the counter in Django admin under **Hit counter → Counter settings**
(`/admin/hit_counter/countersettings/`). There is a single settings record;
changes take effect on the next request without reloading the web app.
Each field is validated when you save. Until you first save the record, the
defaults below apply.

| Admin field | Default | Purpose |
| --- | --- | --- |
| Allowed origins | `https://9trees.github.io` | One exact browser origin per line, without paths or trailing slashes |
| Time zone | `UTC` | IANA timezone for daily counts, e.g. `Asia/Kolkata` |
| Trusted proxy IPs | empty | One immediate proxy IP per line allowed to provide forwarded client IPs |
| GeoIP database path | empty | Absolute filename of a local GeoLite2 City `.mmdb` database on the server |

Only admin users with permission to change counter settings can edit them.
Django core settings such as `DJANGO_SECRET_KEY` and `DJANGO_DEBUG` still use
environment variables; they are needed before the database can be read.

An origin covers an entire host, e.g. `https://9trees.github.io`, not an
individual repository path. Include your custom domain or form host separately.
JSON preflight requests are supported. Cookies/credentials are not used by these
public endpoints; other apps retain their normal CSRF behavior.

**Origin filtering is not authentication or anti-fraud protection.** Non-browser
clients can omit or spoof Origin and inflate counts. Requests without Origin are
accepted for scripts/webhooks. This lightweight personal counter has no rate
limiter, deduplication, or bot filter. Do not embed a private API key in public
GitHub Pages JavaScript. Add host/proxy-level rate limits if abuse becomes a
concern; do not use these counts for billing or security decisions.

### Client IP behind PythonAnywhere's proxy

By default, the counter uses `REMOTE_ADDR` and ignores forwarded headers. Behind
a proxy this may be the proxy's address rather than the visitor's.
[PythonAnywhere documents](https://help.pythonanywhere.com/pages/WebAppClientIPAddresses)
that `REMOTE_ADDR` is its load balancer and the **last** `X-Forwarded-For`
entry is the address received by that load balancer. This is the entry the
counter uses when proxy trust is enabled.
Before enabling trust, confirm the actual immediate proxy IPs from your hosted
request's `REMOTE_ADDR` and your provider's configuration. Only list controlled proxy
IPs that append the real peer IP to `X-Forwarded-For` (or overwrite it with the
verified client IP). The counter uses the **last** entry, not a caller-supplied
first entry. Multiple trusted proxy layers require additional configuration/code;
do not enable this option blindly or trust arbitrary addresses.

### Local location lookup

Obtain a GeoLite2 **City** database from MaxMind under its applicable account,
license, and attribution terms. Upload it outside publicly served/static folders
and enter its full filename in **GeoIP database path**. Keep it updated separately.
No visitor IPs are sent to an external geolocation service.

Country, region and city are approximate IP-based locations, not GPS positions.
VPNs/proxies can make them inaccurate. Every hit has an explicit status:

- `found`: database returned a record (some place names may still be empty).
- `not_configured`: no database path set.
- `not_found`: no database record for the IP (common for private/local addresses).
- `lookup_failed`: missing, unreadable or invalid database; a server error is
  logged. The hit is still recorded.

Only authenticated, authorized Django admin users can view IP/location history.
Hits cannot be added or edited through admin; authorized users may delete them.
Deleting hits reduces totals, and deleting a page deletes its hit history.
IP addresses and approximate location may be personal data: provide an appropriate
privacy notice, restrict admin access, protect backups, and choose a retention
period suitable for your use. There is no automatic retention cleanup; counts
are calculated from retained hit records.

## PythonAnywhere deployment

These changes do not automatically deploy or change your hosted app.

1. Back up the existing SQLite database, then upload/pull the updated project.
2. In a PythonAnywhere Bash console, activate the **same virtualenv configured
   on the Web tab**, change to the project directory, and run:

   ```sh
   pip install -r requirements.txt
   python manage.py check
   python manage.py migrate
   ```

3. For the existing deployment, set `DJANGO_DEBUG=False` and a private
   `DJANGO_SECRET_KEY` in the WSGI configuration rather than relying on
   development defaults. Review the host's HTTPS/proxy setup before enabling
   production settings.
4. If needed, create an admin login with `python manage.py createsuperuser`.
5. Reload the app on PythonAnywhere's **Web** tab.
6. Open `/admin/`, review **Counter settings**, create your Page records, then
   embed the browser snippet.
7. From an allowed page's browser developer tools, verify a POST returns 201
   and increments both counters, and GET returns counts without incrementing.
   Check the stored client IP before trusting location results.

The dependency pins retain this repository's Python 3.8 compatibility.
Python 3.8 and Django 4.2 are past their upstream security-support windows as of
October 2026; plan a separate upgrade to supported Python/Django releases before
treating this as a hardened public service.

## Local validation

With the project environment activated:

```sh
python manage.py check
python manage.py makemigrations hit_counter --check --dry-run
python manage.py test hit_counter
```

Tests use a separate test database, exercise CORS with CSRF checks enabled, check
UTC and daylight-saving boundaries, and simulate GeoIP results without network
requests or a downloaded database.

The repository-wide migration check currently also reports unrelated existing
model/migration differences in the todo and meal-planner apps. Those are not
changed by the counter migration.
