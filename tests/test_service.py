import json
import struct
from fastapi.testclient import TestClient
from backend.app import app
from tests.test_tracking import jpeg
from scripts.make_fixtures import render_frame,BOXES


def packet(frame_id,t,image):
    h=json.dumps({'frame_id':frame_id,'capture_t':t}).encode()
    return struct.pack('<I',len(h))+h+jpeg(image)


def test_health_and_websocket_camera_selection():
    with TestClient(app) as client:
        health=client.get('/api/health').json()
        assert health['status']=='ok' and not health['npu_verified']
        with client.websocket_connect('/ws') as ws:
            assert ws.receive_json()['type']=='ready'
            ws.send_bytes(packet(1,1.,render_frame(0)[0]))
            r=ws.receive_json();assert r['frame_id']==1 and r['tracking']=='unselected'
            ws.send_json({'type':'select','frame_id':1,'boxes':BOXES,'request_id':42})
            r=ws.receive_json();assert r['type']=='selected' and r['request_id']==42
            ws.send_bytes(b'broken')
            assert ws.receive_json()['type']=='error'


def test_external_host_rejected():
    with TestClient(app) as client:
        assert client.get('/api/health',headers={'host':'evil.example'}).status_code==400
