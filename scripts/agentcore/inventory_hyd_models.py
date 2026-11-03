#!/usr/bin/env python3
"""Inventory Bedrock models in ap-south-2 (Hyderabad) and probe live invoke authorization."""
from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import boto3
from botocore.exceptions import ClientError

REGION = "ap-south-2"
OUT = Path(__file__).resolve().parents[2] / "deploy" / "agentcore" / "hyd_model_inventory.json"


def main() -> int:
    br = boto3.client("bedrock", region_name=REGION)
    rt = boto3.client("bedrock-runtime", region_name=REGION)

    fms = br.list_foundation_models().get("modelSummaries") or []
    cands = []
    for m in fms:
        mid = m.get("modelId") or ""
        outs = set(m.get("outputModalities") or [])
        if "TEXT" not in outs:
            continue
        cands.append(
            {
                "modelId": mid,
                "provider": m.get("providerName"),
                "name": m.get("modelName"),
                "lifecycle": (m.get("modelLifecycle") or {}).get("status"),
                "input": sorted(set(m.get("inputModalities") or [])),
                "output": sorted(outs),
                "inferenceTypes": m.get("inferenceTypesSupported") or [],
            }
        )

    try:
        profiles = br.list_inference_profiles().get("inferenceProfileSummaries") or []
    except Exception as exc:  # noqa: BLE001
        profiles = [{"error": str(exc)[:200]}]

    def check_one(mid: str):
        avail = None
        try:
            a = br.get_foundation_model_availability(modelId=mid)
            avail = {
                "authorizationStatus": a.get("authorizationStatus"),
                "entitlementAvailability": a.get("entitlementAvailability"),
                "agreementAvailability": (a.get("agreementAvailability") or {}).get("status"),
                "regionAvailability": a.get("regionAvailability"),
            }
        except ClientError as e:
            err = e.response.get("Error", {})
            avail = {"error": f"{err.get('Code')}: {err.get('Message', '')[:160]}"}

        invoke = None
        low = mid.lower()
        try_invoke = not any(
            x in low for x in ["embed", "image", "tts", "transcribe", "rerank", "canvas"]
        )
        if try_invoke:
            try:
                resp = rt.converse(
                    modelId=mid,
                    messages=[{"role": "user", "content": [{"text": "Reply with OK"}]}],
                    inferenceConfig={"maxTokens": 8},
                )
                text = (
                    resp.get("output", {})
                    .get("message", {})
                    .get("content", [{}])[0]
                    .get("text", "")
                )
                invoke = {"ok": True, "text": (text or "")[:40]}
            except ClientError as e:
                err = e.response.get("Error", {})
                invoke = {
                    "ok": False,
                    "code": err.get("Code"),
                    "message": err.get("Message", "")[:180],
                }
            except Exception as e:  # noqa: BLE001
                invoke = {"ok": False, "code": type(e).__name__, "message": str(e)[:180]}
        return mid, avail, invoke

    results = {}
    with ThreadPoolExecutor(max_workers=6) as ex:
        futs = [ex.submit(check_one, c["modelId"]) for c in cands]
        for fut in as_completed(futs):
            mid, avail, invoke = fut.result()
            results[mid] = {"availability": avail, "invoke": invoke}

    authorized = []
    invoke_ok = []
    for c in cands:
        mid = c["modelId"]
        r = results.get(mid, {})
        a = r.get("availability") or {}
        inv = r.get("invoke")
        row = {**c, "availability": a, "invoke": inv}
        if a.get("authorizationStatus") == "AUTHORIZED":
            authorized.append(row)
        if inv and inv.get("ok"):
            invoke_ok.append(row)

    profile_invoke = []
    if isinstance(profiles, list):
        for p in profiles:
            pid = p.get("inferenceProfileId") or p.get("inferenceProfileArn")
            if not pid:
                continue
            if any(x in pid.lower() for x in ["embed", "image", "canvas"]):
                continue
            try:
                resp = rt.converse(
                    modelId=pid,
                    messages=[{"role": "user", "content": [{"text": "Reply with OK"}]}],
                    inferenceConfig={"maxTokens": 8},
                )
                text = (
                    resp.get("output", {})
                    .get("message", {})
                    .get("content", [{}])[0]
                    .get("text", "")
                )
                profile_invoke.append({"id": pid, "ok": True, "text": (text or "")[:40]})
            except ClientError as e:
                err = e.response.get("Error", {})
                profile_invoke.append(
                    {
                        "id": pid,
                        "ok": False,
                        "code": err.get("Code"),
                        "message": err.get("Message", "")[:160],
                    }
                )
            if len(profile_invoke) >= 30:
                break

    all_text = []
    for c in sorted(cands, key=lambda x: x["modelId"]):
        r = results.get(c["modelId"], {})
        a = r.get("availability") or {}
        inv = r.get("invoke") or {}
        all_text.append(
            {
                "modelId": c["modelId"],
                "provider": c["provider"],
                "lifecycle": c["lifecycle"],
                "authorization": a.get("authorizationStatus") or a.get("error"),
                "entitlement": a.get("entitlementAvailability"),
                "regionAvailability": a.get("regionAvailability"),
                "invoke_ok": bool(inv.get("ok")),
                "invoke_error": None
                if inv.get("ok")
                else (inv.get("code") or inv.get("message")),
            }
        )

    out = {
        "region": REGION,
        "foundation_model_count_listed": len(fms),
        "text_output_candidates": len(cands),
        "inference_profiles_listed": len(profiles) if isinstance(profiles, list) else profiles,
        "AUTHORIZED_count": len(authorized),
        "AUTHORIZED_models": [
            {
                "modelId": x["modelId"],
                "provider": x["provider"],
                "lifecycle": x["lifecycle"],
                "invoke": x["invoke"],
            }
            for x in authorized
        ],
        "invoke_ok_count": len(invoke_ok),
        "invoke_ok_models": [
            {
                "modelId": x["modelId"],
                "provider": x["provider"],
                "text": (x.get("invoke") or {}).get("text"),
            }
            for x in invoke_ok
        ],
        "all_text_models": all_text,
        "sample_profile_invokes": profile_invoke,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(out, indent=2))
    print(f"\nWrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
