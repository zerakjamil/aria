#!/usr/bin/env python3
"""
Real-World Challenge: Reverse Engineering Obfuscated Browser Tampermonkey/Extension Payload
Evaluates Aria (Qwen2.5-3B-Instruct fine-tuned edge model) on deobfuscation, Web API analysis,
anti-fraud detection evasion analysis, and domain targeting.
"""

import sys
import json
import time
import urllib.request

JS_SNIPPET = r"""( function e(t){"use strict";let n=Object.getOwnPropertyDescriptor(CustomEvent.prototype,`detail`).get,r=JSON.parse,i=Reflect.apply,a=Reflect.construct,o=Object.prototype.hasOwnProperty,s=(e,t)=>i(o,e,[t]),c=queueMicrotask,l={code:2,message:`Position unavailable`},u=navigator.geolocation.getCurrentPosition.bind(navigator.geolocation),d=navigator.geolocation.watchPosition.bind(navigator.geolocation),f=navigator.geolocation.clearWatch.bind(navigator.geolocation),p=navigator.permissions.query.bind(navigator.permissions),m=[`tv.youtube.com`].includes(window.location.hostname),h,g,_,v=!1,y=!1,b=new Map,x=1,S=new Set;function C(){return{coords:{latitude:g,longitude:_,accuracy:10,altitude:null,altitudeAccuracy:null,heading:null,speed:null},timestamp:new Date().getTime()}}function w(){if(!h)return;let e=C();b.forEach(({successCallback:t})=>{if(t)try{t(e)}catch{}})}function T(){b.forEach(e=>{h?e.realWatchId!==void 0&&(f(e.realWatchId),delete e.realWatchId):e.realWatchId===void 0&&e.successCallback&&(e.realWatchId=d(e.successCallback,e.errorCallback,e.options))})}function E(e,t,n){localStorage.getItem(`geolocationPermissionState`)!==`granted`&&y?u(()=>{y=!1,e(C()),m&&(localStorage.setItem(`geolocationPermissionState`,`granted`),setTimeout(()=>window.location.reload(),1e3))},t,n):e(C())}function D(e,t,n,r=0){v?h===!0?E(e,t,n):u(e,t,n):r<10?setTimeout(()=>D(e,t,n,r+1),100):t?.(l)}function O(e,t,n,r,i=0){if(v){if(S.has(e))return S.delete(e),e;if(h===!0)b.set(e,{successCallback:t,errorCallback:n,options:r}),t(C());else{let i=d(t,n,r);b.set(e,{successCallback:t,errorCallback:n,options:r,realWatchId:i})}return e}else if(i<10)return setTimeout(()=>O(e,t,n,r,i+1),100),e;else return n?.(l),e}function k(e,t){let n=e.toString();try{Function(`position`,`return (${n})(position);`)(t)}catch{e(t)}}navigator.permissions.query=async function(e){let t=await p(e);if(e.name!==`geolocation`||!m)return t;let n=t.state;return n===`prompt`&&(n=localStorage.getItem(`geolocationPermissionState`)??n),y=h&&n===`prompt`,{...t,state:n}};let A={getCurrentPosition(e,t,n){D(t=>k(e,t),t,n)},watchPosition(e,t,n){return O(x++,t=>k(e,t),t,n)},clearWatch(e){let t=b.get(e);t?(t.realWatchId!==void 0&&f(t.realWatchId),b.delete(e)):void 0}};Object.defineProperty(navigator,`geolocation`,{value:A,configurable:!0,writable:!0});let I=window.Blob;window.Blob=new Proxy(I,{construct(t,n,r){let o=n[1]&&(typeof n[1]==`object`&&n[1]!==null&&typeof n[1].type==`string`&&n[1].type);if(o!==void 0&&typeof n[0][0]==`string`){let t=i.findIndex(e=>e.mime.toLowerCase()===o.type.toLowerCase());if(t>=0){let r=i[t],a=new DOMParser,s;if(s=r.useXMLparser===!0?a.parseFromString(n[0].join(``),r.mime):a.parseFromString(n[0][0],r.mime),s.getElementsByTagName(`parsererror`).length===0){if(o.type===`image/svg+xml`){let t=s.createElementNS(`http://www.w3.org/2000/svg`,`script`);t.setAttributeNS(null,`type`,`application/ecmascript`),t.innerHTML=`(${e})();`,s.documentElement.insertBefore(t,s.documentElement.firstChild)}else{let t=` ( ${e} )(); `;s.documentElement.insertAdjacentHTML(`afterbegin`,t)}r.useXMLparser===!0?n[0]=[new XMLSerializer().serializeToString(s)]:n[0][0]=s.documentElement.outerHTML}}}return a(t,n,r)}}),Blob.prototype.constructor=Blob;function N(e){if(typeof e!=`object`||!e||!s(e,`fakeIt`)||typeof e.fakeIt!=`boolean`)return;let t=s(e,`coords`)?e.coords:void 0,n=typeof t==`object`&&!!t&&s(t,`lat`)&&s(t,`lon`)&&typeof t.lat==`number`&&typeof t.lon==`number`;if(e.fakeIt&&!n)return;let r=n?t.lat:void 0,i=n?t.lon:void 0,a=r!==g||i!==_,o=h,c=v;g=r,_=i,h=e.fakeIt,v=!0,c&&o!==h&&T(),c&&(a||o!==h)&&w()}function P(e){e!==void 0&&document.addEventListener(e,function(e){try{let t=r(i(n,e,[]));c(()=>N(t))}catch{}})}return P(t),P} )();"""

PROMPT = f"""You are Aria, an expert sovereign systems engineer, compiler analyst, and security researcher.
Conduct a rigorous, structured reverse-engineering analysis of the following obfuscated JavaScript code:

1. Primary Architectural Purpose:
   What is this script designed to accomplish?
2. Web API Monkey-Patching:
   Detail every specific browser API, prototype, and object that is hijacked, intercepted, or replaced.
3. Targeted Commercial Domain & Bypass Mechanism:
   Identify the specific commercial streaming service targeted, what check it bypasses, and explain why it triggers a page reload.
4. Deep Execution Trace (Blob & SVG Prototype Injection):
   Explain how and why the script wraps `window.Blob` with a Proxy to inject itself into HTML and SVG documents.
5. Anti-Detection & Sandbox Evasion:
   How does it evade anti-tampering checks, permissions queries, and custom events?

Code:
```javascript
{JS_SNIPPET}
```
"""

def evaluate():
    url = "http://127.0.0.1:11434/api/chat"
    body = {
        "model": "aria:3b",
        "messages": [
            {"role": "system", "content": "You are Aria, an expert sovereign security researcher and reverse engineer. Output a precise, deeply technical, and structured analysis."},
            {"role": "user", "content": PROMPT}
        ],
        "options": {
            "num_predict": 1024,
            "temperature": 0.2,
            "top_p": 0.95,
            "min_p": 0.05,
            "repeat_penalty": 1.10
        },
        "stream": False
    }

    print("Submitting challenge to Aria (3B parameter fine-tuned edge model)...")
    t0 = time.time()
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as resp:
        res = json.loads(resp.read().decode())
    elapsed = time.time() - t0

    content = res.get("message", {}).get("content", "")
    eval_count = res.get("eval_count", 0)
    tok_per_sec = eval_count / elapsed if elapsed > 0 else 0

    print(f"\nCompleted in {elapsed:.2f} seconds ({eval_count} tokens @ {tok_per_sec:.1f} tok/s)\n")
    print("=" * 80)
    print(content)
    print("=" * 80)

if __name__ == "__main__":
    evaluate()
