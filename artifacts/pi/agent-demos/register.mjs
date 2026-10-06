// pi-ai 전체(openai 등 의존성 다수)를 설치하지 않고, agent가 쓰는 함수만 가진 shim으로 연결한다.
import { register } from "node:module";
register("./loader.mjs", import.meta.url);
