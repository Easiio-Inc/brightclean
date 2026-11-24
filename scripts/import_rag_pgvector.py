#!/usr/bin/env python3
"""Idempotently import JSON knowledge into configured pgvector storage."""
import argparse, json, os, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/'backend'))
from rag_store import configured_store

def main():
 p=argparse.ArgumentParser(); p.add_argument('--site-id',required=True); p.add_argument('--input',type=Path,default=ROOT/'data/rag-content.json'); p.add_argument('--dry-run',action='store_true'); args=p.parse_args()
 raw=json.loads(args.input.read_text()); items=raw.get('sites',{}).get(args.site_id,[])
 print(f'{len(items)} documents for tenant {args.site_id}'+(' (dry run)' if args.dry_run else ''))
 if args.dry_run:return
 store=configured_store();
 if not store: raise SystemExit('EASIIO_RAG_DATABASE_URL and embedding API key are required')
 for item in items:
  store.ingest(args.site_id,{'document_id':item['content_id'],'title':item.get('title',''),'content':item.get('content',''),'source_url':item.get('url',''),'original_filename':item.get('original_filename',''),'metadata':item.get('metadata',{})})
 print('Import complete; content hashes and tenant/document keys make reruns idempotent.')
if __name__=='__main__': main()
