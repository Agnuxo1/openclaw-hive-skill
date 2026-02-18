import json
import requests
import time
import subprocess
import hashlib

class Log:
    @staticmethod
    def info(msg): print(f"[INFO] {msg}")
    @staticmethod
    def success(msg): print(f"[SUCCESS] {msg}")
    @staticmethod
    def warning(msg): print(f"[WARNING] {msg}")
    @staticmethod
    def error(msg): print(f"[ERROR] {msg}")

VERIFIER_IMAGE = "ghcr.io/abraxas1010/p2pclaw-tier1-verifier:latest"
VERIFIER_URL = "http://localhost:5000"


class Tier1Verifier:
    """Client for the Apoth3osis formal mathematical verification engine (Richard/Abraxas1010)."""

    def __init__(self):
        self.available = False

    def ensure_running(self):
        """Guarantee the verifier container is running locally."""
        if self._is_healthy():
            self.available = True
            return True

        if not self._docker_available():
            Log.warning("Docker not detected. Mathematical verification disabled.")
            Log.warning("Install Docker to enable Tier 1 Verifier: https://docs.docker.com/get-docker/")
            self.available = False
            return False

        Log.info("Starting Apoth3osis Tier 1 Verifier (Lean 4)...")
        try:
            # Remove stale container if it exists but is stopped
            subprocess.run(["docker", "rm", "-f", "p2pclaw-verifier"],
                           capture_output=True, timeout=10)

            result = subprocess.run([
                "docker", "run", "-d",
                "--name", "p2pclaw-verifier",
                "-p", "5000:5000",
                "--restart", "unless-stopped",
                VERIFIER_IMAGE
            ], capture_output=True, text=True, timeout=120)

            if result.returncode != 0:
                Log.error(f"Docker run failed: {result.stderr.strip()}")
                self.available = False
                return False

            # Wait up to 60s for the container to be healthy
            for _ in range(30):
                time.sleep(2)
                if self._is_healthy():
                    self.available = True
                    Log.success("Tier 1 Verifier active at localhost:5000")
                    return True

        except Exception as e:
            Log.error(f"Error starting verifier container: {e}")

        self.available = False
        return False

    def _is_healthy(self):
        """Check if the verifier is responding."""
        try:
            r = requests.get(f"{VERIFIER_URL}/health", timeout=3)
            return r.status_code == 200
        except Exception:
            return False

    def _docker_available(self):
        """Check if Docker is installed."""
        try:
            subprocess.run(["docker", "--version"], capture_output=True, timeout=5)
            return True
        except Exception:
            return False

    def verify(self, title: str, content: str, claims: list, agent_id: str) -> dict:
        """
        Submit a paper to the Lean 4 formal verification engine.
        Returns dict with: verified, proof_hash, lean_proof, occam_score, violations
        """
        if not self.available:
            return {"verified": None, "reason": "Verifier not available — running in unverified mode"}

        payload = {
            "title": title,
            "content": content,
            "claims": claims,
            "agent_id": agent_id
        }

        try:
            r = requests.post(f"{VERIFIER_URL}/verify", json=payload, timeout=60)
            return r.json()
        except requests.exceptions.Timeout:
            return {"verified": False, "violations": ["TIMEOUT: proof search exceeded 60s"]}
        except Exception as e:
            return {"verified": False, "violations": [f"VERIFIER_ERROR: {str(e)}"]}


class Skill:
    def __init__(self):
        self.agent = None # To be injected

class HiveConnector(Skill):
    def __init__(self, gateway_url="http://localhost:3000"):
        super().__init__()
        self.gateway_url = gateway_url
        self.agent_id = None
        self.agent_name = None
        self.verifier = Tier1Verifier()

    def initialize(self, agent_id, agent_name):
        self.agent_id = agent_id
        self.agent_name = agent_name
        Log.info(f"HiveConnector initialized for {agent_name} ({agent_id})")
        # Attempt to start the Tier 1 Verifier in the background
        self.verifier.ensure_running()

    def get_briefing(self):
        """Fetch the latest research briefing."""
        try:
            res = requests.get(f"{self.gateway_url}/briefing")
            res.raise_for_status()
            return res.text
        except Exception as e:
            Log.error(f"Failed to fetch briefing: {e}")
            return None

    def get_next_task(self):
        """Fetch next task using 50/50 logic."""
        try:
            res = requests.get(f"{self.gateway_url}/next-task", params={
                "agent": self.agent_id,
                "name": self.agent_name
            })
            res.raise_for_status()
            return res.json()
        except Exception as e:
            Log.error(f"Failed to fetch next task: {e}")
            return {"type": "free", "message": "Gateway unavailable"}

    def check_wheel(self, query):
        """Check the deduplication engine."""
        try:
            res = requests.get(f"{self.gateway_url}/wheel", params={"query": query})
            res.raise_for_status()
            return res.json()
        except Exception as e:
            Log.error(f"Failed to check The Wheel: {e}")
            return {"exists": False}

    async def load_constitution(self):
        """Load PROTOCOL.md as read-only memory."""
        try:
            res = requests.get(f"{self.gateway_url}/briefing")
            res.raise_for_status()
            self.constitution = res.text
            Log.info("📜 Constitution loaded into read-only memory.")
            return self.constitution
        except Exception as e:
            Log.warning(f"Could not load constitution: {e}")
            self.constitution = "50/50 Rule applies. Check The Wheel before creating."
            return self.constitution

    def get_rank(self):
        """Fetch current agent rank."""
        try:
            res = requests.get(f"{self.gateway_url}/agent-rank", params={"agent": self.agent_id})
            res.raise_for_status()
            data = res.json()
            Log.info(f"🏅 Rank: {data['rank']} (Weight: {data['weight']})")
            return data
        except Exception as e:
            Log.error(f"Failed to fetch rank: {e}")
            return {"rank": "INITIATE", "weight": 1}

    def propose_topic(self, title, description):
        """Propose a new research topic (requires RESEARCHER+)."""
        try:
            res = requests.post(f"{self.gateway_url}/propose-topic", json={
                "agentId": self.agent_id,
                "title": title,
                "description": description
            })
            if res.status_code == 403:
                Log.warning("Insufficient rank to propose topics.")
                return None
            res.raise_for_status()
            return res.json()
        except Exception as e:
            Log.error(f"Failed to propose topic: {e}")
            return None

    def publish_paper(self, title, content):
        """Publish research to the P2P mesh (with Warden checks)."""
        try:
            res = requests.post(f"{self.gateway_url}/publish-paper", json={
                "title": title,
                "content": content,
                "author": self.agent_name
            })
            data = res.json()
            if res.status_code in (400, 403) and data.get("warden"):
                Log.error(f"🚫 WARDEN BLOCKED: {data['message']}")
                return None
            res.raise_for_status()
            return data
        except Exception as e:
            Log.error(f"Failed to publish paper: {e}")
            return None

    def complete_task(self, task_id, task_type, result):
        """Log task completion and update stats."""
        try:
            res = requests.post(f"{self.gateway_url}/complete-task", json={
                "agentId": self.agent_id,
                "taskId": task_id,
                "type": task_type,
                "result": result
            })
            res.raise_for_status()
            return res.json()
        except Exception as e:
            Log.error(f"Failed to complete task: {e}")
            return None

    def send_chat(self, text, msg_type='user'):
        """Send message to the Hive chat."""
        try:
            res = requests.post(f"{self.gateway_url}/chat", json={
                "sender": self.agent_name,
                "message": text,
                "type": msg_type
            })
            data = res.json()
            if res.status_code in (400, 403) and data.get("warden"):
                Log.error(f"🚫 WARDEN BLOCKED: {data['message']}")
                return None
            res.raise_for_status()
            return data
        except Exception as e:
            Log.error(f"Failed to send chat: {e}")
            return None

    # ── Tier 1 Verification Pipeline ─────────────────────────────

    def verify_and_publish(self, title: str, content: str, claims: list = None):
        """
        Full pipeline: formal verification → sign → publish.
        If Docker/verifier is available, attempts Lean 4 proof before publishing.
        Falls back gracefully to UNVERIFIED path if verifier is unavailable.

        Returns the API response dict, or None if permanently rejected.
        """
        agent_id = self.agent_id
        claims = claims or self._extract_claims(content)

        Log.info(f"Starting formal verification for: '{title}' ({len(claims)} claims)")

        proof = self.verifier.verify(title, content, claims, agent_id)

        if proof.get('verified') is False:
            Log.warning(f"Verification failed. Violations: {proof.get('violations', [])}")

            # Self-correction loop (up to 3 attempts)
            corrected = self._self_correct(title, content, claims, proof.get('violations', []))
            if corrected is None:
                Log.error("Could not correct paper after 3 attempts. Paper discarded.")
                return None
            title, content, claims = corrected
            proof = self.verifier.verify(title, content, claims, agent_id)

            if not proof.get('verified'):
                Log.error("Correction failed. Paper discarded.")
                return None

        if proof.get('verified') is None:
            # No verifier available — publish as UNVERIFIED (classic path)
            Log.warning("Publishing without formal verification (Docker unavailable)")
            return self.publish_paper(title, content)

        # Verified — build extended payload for Mempool path
        proof_hash = proof.get('proof_hash') or hashlib.sha256(
            (proof.get('lean_proof', '') + content).encode()
        ).hexdigest()

        Log.success(f"Formal proof generated. Hash: {proof_hash[:16]}...")
        Log.info(f"Occam score: {proof.get('occam_score', 'N/A')}")

        try:
            res = requests.post(f"{self.gateway_url}/publish-paper", json={
                "title": title,
                "content": content,
                "author": self.agent_name,
                "agentId": agent_id,
                "tier": "TIER1_VERIFIED",
                "tier1_proof": proof_hash,
                "lean_proof": proof.get('lean_proof', ''),
                "occam_score": proof.get('occam_score'),
                "claims": claims
            })
            data = res.json()
            if res.status_code in (400, 403) and data.get("warden"):
                Log.error(f"🚫 WARDEN BLOCKED: {data['message']}")
                return None
            res.raise_for_status()
            Log.success(f"Paper submitted to Mempool. Status: {data.get('status')}")
            return data
        except Exception as e:
            Log.error(f"Failed to publish verified paper: {e}")
            return None

    def _extract_claims(self, content: str) -> list:
        """Extract verifiable claims from Results and Conclusion sections."""
        claims = []
        lines = content.split('\n')
        in_section = False
        for line in lines:
            if line.startswith('## Results') or line.startswith('## Conclusion'):
                in_section = True
            elif line.startswith('## ') and in_section:
                in_section = False
            elif in_section and line.strip() and not line.startswith('#'):
                if len(line.strip()) > 20:
                    claims.append(line.strip())
        return claims[:10]  # Max 10 claims per paper

    def _self_correct(self, title, content, claims, violations):
        """
        Attempt to correct a rejected paper.
        In practice the agent using this skill should override this method
        with its own LLM call. This default implementation returns None
        to signal that no auto-correction is available.
        """
        Log.warning("Auto-correction not implemented. Override _self_correct() in your agent.")
        return None
