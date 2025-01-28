from flask import Flask, request, jsonify
import os
import subprocess
import smtplib
from email.mime.text import MIMEText

app = Flask(__name__)

# Configuration (can also be moved to a separate file like `config/settings.py`)
REPO_URL = os.getenv("REPO_URL", "https://github.com/Pazl-Infolyte-1/BUZZ-APP-BACK-END.git")
BRANCH_NAME = os.getenv("BRANCH_NAME", "development")
PROJECT_DIR = os.getenv("PROJECT_DIR", "/home/BUZZ-APP-BACK-END")
EMAIL_FROM = os.getenv("EMAIL_FROM", "jenkins@pazl.info")
EMAIL_TO = os.getenv("EMAIL_TO", "ananda.s@pazl.info")
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
SMTP_USERNAME = os.getenv("SMTP_USERNAME", "sanjay@pazl.in")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "hecivtisnkjyufqh")


def send_email(subject, body):
    """Send email notifications."""
    try:
        msg = MIMEText(body, "html")
        msg["Subject"] = subject
        msg["From"] = EMAIL_FROM
        msg["To"] = EMAIL_TO

        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USERNAME, SMTP_PASSWORD)
            server.sendmail(EMAIL_FROM, [EMAIL_TO], msg.as_string())
    except Exception as e:
        print(f"Error sending email: {e}")


def execute_command(command, cwd=None):
    """Execute a shell command and return the output."""
    result = subprocess.run(command, shell=True, cwd=cwd, capture_output=True, text=True)
    if result.returncode != 0:
        raise Exception(f"Command failed: {command}\nError: {result.stderr}")
    return result.stdout.strip()


@app.route("/webhook", methods=["POST"])
def github_webhook():
    """GitHub webhook endpoint."""
    try:
        payload = request.json
        if not payload or "ref" not in payload:
            return jsonify({"message": "Invalid payload"}), 400

        branch = payload["ref"].split("/")[-1]
        if branch != BRANCH_NAME:
            return jsonify({"message": "Branch does not match, skipping"}), 200

        # Pull the latest code
        execute_command(f"git fetch origin {BRANCH_NAME}", cwd=PROJECT_DIR)
        execute_command(f"git reset --hard origin/{BRANCH_NAME}", cwd=PROJECT_DIR)

        # Get the latest commit logs
        commit_logs = execute_command("git log --oneline -n 10", cwd=PROJECT_DIR)

        # Build and start Docker containers
        execute_command("docker-compose build", cwd=PROJECT_DIR)
        execute_command("docker-compose up -d", cwd=PROJECT_DIR)

        # Send success email
        send_email(
            subject=f"Build Success: BUZZ-APP-BACK-END on {BRANCH_NAME}",
            body=f"""
                <p>The latest code has been pulled, and Docker containers have been successfully built and started.</p>
                <p><b>Commit Details:</b><br>{commit_logs.replace('\\n', '<br>')}</p>
            """
        )
        return jsonify({"message": "Build and deployment successful"}), 200

    except Exception as e:
        # Send failure email
        send_email(
            subject=f"Build Failed: BUZZ-APP-BACK-END on {BRANCH_NAME}",
            body=f"<p>Error: {str(e)}</p>"
        )
        return jsonify({"message": f"Build failed: {str(e)}"}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=6000)
