"""Run with python run.py. Live operation never contacts a cloud service."""
import argparse
import threading
import webbrowser
import uvicorn

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--port',type=int,default=8765)
    parser.add_argument('--no-browser',action='store_true')
    args=parser.parse_args()
    if not args.no_browser:
        threading.Timer(1.2,lambda:webbrowser.open(f'http://127.0.0.1:{args.port}')).start()
    uvicorn.run('backend.app:app',host='127.0.0.1',port=args.port,ws_max_size=4_000_000,ws_max_queue=1,log_level='info')
