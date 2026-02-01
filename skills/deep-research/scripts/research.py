#!/usr/bin/env python3
"""
Gemini Deep Research Skill - Execute autonomous multi-step research tasks.

Uses Google's Deep Research Agent for comprehensive, cited research reports.
Research tasks take 2-10 minutes but produce detailed analysis.
"""

import argparse
import asyncio
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, AsyncIterator, Callable, Dict, List, Optional

try:
    import httpx
except ImportError:
    print("Error: httpx not installed. Run: pip install httpx", file=sys.stderr)
    sys.exit(1)

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv is optional


class DeepResearchError(Exception):
    """Custom exception for Deep Research API errors."""
    pass


class HistoryManager:
    """Manage local research history cache."""

    def __init__(self, cache_dir: Optional[str] = None):
        default_dir = os.path.expanduser("~/.cache/deep-research")
        self.cache_dir = Path(cache_dir or os.getenv("DEEP_RESEARCH_CACHE_DIR", default_dir))
        self.history_file = self.cache_dir / "history.json"
        self._ensure_cache_dir()

    def _ensure_cache_dir(self):
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _load_history(self) -> Dict:
        if self.history_file.exists():
            try:
                return json.loads(self.history_file.read_text())
            except (json.JSONDecodeError, IOError):
                return {"interactions": []}
        return {"interactions": []}

    def _save_history(self, history: Dict):
        self.history_file.write_text(json.dumps(history, indent=2))

    def add_interaction(self, interaction_id: str, query: str, status: str = "started"):
        history = self._load_history()
        for item in history["interactions"]:
            if item["id"] == interaction_id:
                item["status"] = status
                item["updated_at"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
                self._save_history(history)
                return
        history["interactions"].insert(0, {
            "id": interaction_id,
            "query": query[:200] + "..." if len(query) > 200 else query,
            "started_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "status": status
        })
        history["interactions"] = history["interactions"][:50]
        self._save_history(history)

    def update_status(self, interaction_id: str, status: str):
        history = self._load_history()
        for item in history["interactions"]:
            if item["id"] == interaction_id:
                item["status"] = status
                item["updated_at"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
                if status == "completed":
                    item["completed_at"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
                break
        self._save_history(history)

    def get_recent(self, limit: int = 10) -> List[Dict]:
        history = self._load_history()
        return history["interactions"][:limit]

    def get_interaction(self, interaction_id: str) -> Optional[Dict]:
        history = self._load_history()
        for item in history["interactions"]:
            if item["id"] == interaction_id:
                return item
        return None


class DeepResearchClient:
    """Client for Gemini Deep Research API."""

    BASE_URL = "https://generativelanguage.googleapis.com/v1beta/interactions"
    AGENT = "deep-research-pro-preview-12-2025"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise DeepResearchError(
                "GEMINI_API_KEY not set. Set it in .env or environment variables."
            )
        self._client: Optional[httpx.AsyncClient] = None
        self.timeout = int(os.getenv("DEEP_RESEARCH_TIMEOUT", "600"))
        self.poll_interval = int(os.getenv("DEEP_RESEARCH_POLL_INTERVAL", "10"))
        self.history = HistoryManager()

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=60.0)
        return self._client

    async def close(self):
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    def _build_prompt(self, query: str, format_spec: Optional[str] = None) -> str:
        prompt = query
        if format_spec:
            prompt += f"\n\nFormat the output with the following structure:\n{format_spec}"
        return prompt

    async def start_research(
        self,
        query: str,
        format_spec: Optional[str] = None,
        previous_interaction_id: Optional[str] = None
    ) -> str:
        prompt = self._build_prompt(query, format_spec)
        client = await self._get_client()

        payload: Dict[str, Any] = {
            "input": prompt,
            "agent": self.AGENT,
            "background": True
        }

        if previous_interaction_id:
            payload["previous_interaction_id"] = previous_interaction_id

        try:
            response = await client.post(
                self.BASE_URL,
                headers={
                    "Content-Type": "application/json",
                    "x-goog-api-key": str(self.api_key)
                },
                json=payload
            )

            if response.status_code != 200:
                error_text = response.text
                raise DeepResearchError(f"API error {response.status_code}: {error_text}")

            data = response.json()
            interaction_id = data.get("id") or data.get("name", "").split("/")[-1]

            if not interaction_id:
                raise DeepResearchError("No interaction ID returned from API")

            self.history.add_interaction(interaction_id, query, "started")
            return interaction_id

        except httpx.HTTPError as e:
            raise DeepResearchError(f"HTTP error: {e}")

    async def get_status(self, interaction_id: str) -> Dict[str, Any]:
        client = await self._get_client()

        try:
            response = await client.get(
                f"{self.BASE_URL}/{interaction_id}",
                headers={"x-goog-api-key": str(self.api_key)},
                timeout=30.0
            )

            if response.status_code != 200:
                return {"status": "error", "error": f"API error: {response.status_code}"}

            data = response.json()
            status = data.get("status", "unknown")

            if status == "completed":
                outputs = data.get("outputs", [])
                if outputs:
                    text = outputs[-1].get("text", "")
                    return {"status": "completed", "result": text, "raw": data}
                return {"status": "completed", "result": None, "raw": data}
            elif status == "failed":
                return {"status": "failed", "error": data.get("error", "Unknown error")}
            else:
                return {"status": status, "raw": data}

        except httpx.HTTPError as e:
            return {"status": "error", "error": str(e)}

    async def wait_for_completion(
        self,
        interaction_id: str,
        timeout: Optional[int] = None,
        poll_interval: Optional[int] = None,
        progress_callback: Optional[Callable[[int, float, str], None]] = None
    ) -> Dict[str, Any]:
        timeout = timeout or self.timeout
        poll_interval = poll_interval or self.poll_interval
        start_time = asyncio.get_event_loop().time()
        poll_count = 0

        while True:
            elapsed = asyncio.get_event_loop().time() - start_time
            if elapsed > timeout:
                self.history.update_status(interaction_id, "timeout")
                return {"status": "timeout", "error": f"Research timed out after {timeout}s"}

            result = await self.get_status(interaction_id)
            poll_count += 1

            if progress_callback:
                progress_callback(poll_count, elapsed, result.get("status", "unknown"))

            if result["status"] == "completed":
                self.history.update_status(interaction_id, "completed")
                return result
            elif result["status"] in ["failed", "error"]:
                self.history.update_status(interaction_id, "failed")
                return result

            await asyncio.sleep(poll_interval)

    async def stream_research(
        self,
        query: str,
        format_spec: Optional[str] = None
    ) -> AsyncIterator[Dict[str, Any]]:
        prompt = self._build_prompt(query, format_spec)
        client = await self._get_client()

        try:
            async with client.stream(
                "POST",
                f"{self.BASE_URL}?alt=sse",
                headers={
                    "Content-Type": "application/json",
                    "x-goog-api-key": str(self.api_key)
                },
                json={
                    "input": prompt,
                    "agent": self.AGENT,
                    "background": True,
                    "stream": True,
                    "agent_config": {
                        "type": "deep-research",
                        "thinking_summaries": "auto"
                    }
                },
                timeout=None
            ) as response:
                interaction_id = None
                buffer = ""

                async for chunk in response.aiter_text():
                    buffer += chunk

                    while "\n\n" in buffer:
                        event_str, buffer = buffer.split("\n\n", 1)

                        if not event_str.strip():
                            continue

                        data_line = None
                        for line in event_str.split("\n"):
                            if line.startswith("data: "):
                                data_line = line[6:]
                                break

                        if not data_line:
                            continue

                        try:
                            event = json.loads(data_line)
                        except json.JSONDecodeError:
                            continue

                        event_type = event.get("event_type", "")

                        if event_type == "interaction.start":
                            interaction_id = event.get("interaction", {}).get("id")
                            if interaction_id:
                                self.history.add_interaction(interaction_id, query, "streaming")
                            yield {"type": "start", "interaction_id": interaction_id}

                        elif event_type == "content.delta":
                            delta = event.get("delta", {})
                            delta_type = delta.get("type")

                            if delta_type == "text":
                                yield {"type": "text", "content": delta.get("text", "")}
                            elif delta_type == "thought_summary":
                                content = delta.get("content", {})
                                yield {"type": "thought", "content": content.get("text", "")}

                        elif event_type == "interaction.complete":
                            if interaction_id:
                                self.history.update_status(interaction_id, "completed")
                            yield {"type": "complete"}

                        elif event_type == "error":
                            if interaction_id:
                                self.history.update_status(interaction_id, "failed")
                            yield {"type": "error", "error": event.get("error", "Unknown error")}

        except httpx.HTTPError as e:
            yield {"type": "error", "error": str(e)}

    def parse_result(self, text: str) -> Optional[Dict]:
        if not text:
            return None

        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass

        json_match = re.search(r'\{[^{}]*"[^"]+"\s*:[^{}]*\}', text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(0))
            except json.JSONDecodeError:
                pass

        return None


def print_progress(poll_count: int, elapsed: float, status: str):
    mins = int(elapsed // 60)
    secs = int(elapsed % 60)
    print(f"\r[{mins:02d}:{secs:02d}] Poll #{poll_count} - Status: {status}", end="", flush=True)


async def cmd_research(args):
    client = DeepResearchClient()

    try:
        if args.stream:
            print(f"Starting streaming research...\n")
            full_text = ""

            async for event in client.stream_research(args.query, args.format):
                if event["type"] == "start":
                    print(f"Interaction ID: {event['interaction_id']}\n")
                elif event["type"] == "thought":
                    print(f"\n[Thinking] {event['content']}\n", file=sys.stderr)
                elif event["type"] == "text":
                    print(event["content"], end="", flush=True)
                    full_text += event["content"]
                elif event["type"] == "complete":
                    print("\n\n[Research Complete]")
                elif event["type"] == "error":
                    print(f"\n[Error] {event['error']}", file=sys.stderr)
                    return 1

            if args.json and full_text:
                parsed = client.parse_result(full_text)
                if parsed:
                    print("\n\n--- Parsed JSON ---")
                    print(json.dumps(parsed, indent=2))
        else:
            previous_id = args.continue_from if hasattr(args, 'continue_from') else None

            print(f"Starting research task...")
            interaction_id = await client.start_research(
                args.query,
                args.format,
                previous_id
            )
            print(f"Interaction ID: {interaction_id}")
            print(f"Estimated time: 2-10 minutes\n")

            if args.no_wait:
                print(f"Research started. Check status with: --status {interaction_id}")
                return 0

            print("Waiting for completion (Ctrl+C to cancel)...")
            result = await client.wait_for_completion(
                interaction_id,
                progress_callback=print_progress
            )
            print()

            if result["status"] == "completed":
                text = result.get("result", "")

                if args.json:
                    parsed = client.parse_result(text)
                    if parsed:
                        print(json.dumps(parsed, indent=2))
                    else:
                        print(json.dumps({"text": text}, indent=2))
                elif args.raw:
                    print(json.dumps(result.get("raw", {}), indent=2))
                else:
                    print("\n--- Research Result ---\n")
                    print(text)

                return 0
            else:
                print(f"\nResearch failed: {result.get('error', 'Unknown error')}")
                return 1

    except DeepResearchError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\n\nCancelled by user.")
        return 130
    finally:
        await client.close()


async def cmd_status(args):
    client = DeepResearchClient()

    try:
        result = await client.get_status(args.interaction_id)

        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"Status: {result['status']}")

            if result["status"] == "completed":
                text = result.get("result", "")
                if text:
                    print(f"\n--- Result Preview ---\n{text[:500]}...")
            elif result["status"] in ["failed", "error"]:
                print(f"Error: {result.get('error', 'Unknown')}")

        return 0 if result["status"] != "error" else 1

    except DeepResearchError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    finally:
        await client.close()


async def cmd_wait(args):
    client = DeepResearchClient()

    try:
        print(f"Waiting for {args.interaction_id}...")
        result = await client.wait_for_completion(
            args.interaction_id,
            progress_callback=print_progress
        )
        print()

        if result["status"] == "completed":
            text = result.get("result", "")

            if args.json:
                parsed = client.parse_result(text)
                if parsed:
                    print(json.dumps(parsed, indent=2))
                else:
                    print(json.dumps({"text": text}, indent=2))
            else:
                print("\n--- Research Result ---\n")
                print(text)

            return 0
        else:
            print(f"Research failed: {result.get('error', 'Unknown error')}")
            return 1

    except DeepResearchError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\n\nCancelled by user.")
        return 130
    finally:
        await client.close()


async def cmd_list(args):
    history = HistoryManager()
    interactions = history.get_recent(args.limit)

    if not interactions:
        print("No research history found.")
        return 0

    if args.json:
        print(json.dumps(interactions, indent=2))
    else:
        print(f"Recent research tasks (last {len(interactions)}):\n")
        for item in interactions:
            status_icon = {
                "completed": "[ok]",
                "failed": "[!!]",
                "started": "[..]",
                "streaming": "[>>]",
                "timeout": "[to]"
            }.get(item.get("status", ""), "[??]")

            print(f"{status_icon} {item['id'][:12]}...")
            print(f"    Query: {item['query'][:60]}{'...' if len(item['query']) > 60 else ''}")
            print(f"    Started: {item.get('started_at', 'N/A')}")
            if item.get("completed_at"):
                print(f"    Completed: {item['completed_at']}")
            print()

    return 0


def main():
    parser = argparse.ArgumentParser(
        description="Gemini Deep Research - Autonomous multi-step research agent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --query "Research the history of Kubernetes"
  %(prog)s --query "Compare Python web frameworks" --format "1. Summary\\n2. Table"
  %(prog)s --query "Analyze EV battery market" --stream
  %(prog)s --query "Research topic" --no-wait
  %(prog)s --status abc123
  %(prog)s --query "Elaborate on point 2" --continue abc123
  %(prog)s --list

Note: Research tasks typically take 2-10 minutes and cost $2-5 per task.
"""
    )

    cmd_group = parser.add_mutually_exclusive_group(required=True)
    cmd_group.add_argument("--query", "-q", help="Research query to execute")
    cmd_group.add_argument("--status", "-s", dest="interaction_id", metavar="ID",
                          help="Check status of a research task")
    cmd_group.add_argument("--wait", "-w", dest="wait_id", metavar="ID",
                          help="Wait for a research task to complete")
    cmd_group.add_argument("--list", "-l", action="store_true",
                          help="List recent research tasks")

    parser.add_argument("--format", "-f", metavar="SPEC",
                       help="Output format specification")
    parser.add_argument("--continue", dest="continue_from", metavar="ID",
                       help="Continue from previous research interaction")
    parser.add_argument("--stream", action="store_true",
                       help="Stream progress in real-time")
    parser.add_argument("--no-wait", action="store_true",
                       help="Start research without waiting for completion")

    parser.add_argument("--json", "-j", action="store_true",
                       help="Output results as JSON")
    parser.add_argument("--raw", "-r", action="store_true",
                       help="Output raw API response")

    parser.add_argument("--limit", type=int, default=10,
                       help="Number of recent tasks to show (default: 10)")

    args = parser.parse_args()

    if args.query:
        exit_code = asyncio.run(cmd_research(args))
    elif args.interaction_id:
        exit_code = asyncio.run(cmd_status(args))
    elif args.wait_id:
        args.interaction_id = args.wait_id
        exit_code = asyncio.run(cmd_wait(args))
    elif args.list:
        exit_code = asyncio.run(cmd_list(args))
    else:
        parser.print_help()
        exit_code = 1

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
