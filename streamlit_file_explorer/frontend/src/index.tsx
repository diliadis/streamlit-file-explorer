import type {
  FrontendRenderer,
  FrontendRendererArgs,
} from "@streamlit/component-v2-lib";
import { StrictMode } from "react";
import { createRoot, type Root } from "react-dom/client";
import Explorer from "./Explorer";
import type { ExplorerData, ExplorerState } from "./types";
import "./style.css";

const roots: WeakMap<FrontendRendererArgs["parentElement"], Root> =
  new WeakMap();
const render: FrontendRenderer<ExplorerState, ExplorerData> = ({
  data,
  parentElement,
  setTriggerValue,
}) => {
  const element = parentElement.querySelector(".react-root");
  if (!element) throw new Error("File explorer root element is missing.");
  let root = roots.get(parentElement);
  if (!root) {
    root = createRoot(element);
    roots.set(parentElement, root);
  }
  root.render(
    <StrictMode>
      <Explorer
        key={data.instance_id}
        data={data}
        send={(event) => setTriggerValue("action", event)}
      />
    </StrictMode>,
  );
  return () => {
    roots.get(parentElement)?.unmount();
    roots.delete(parentElement);
  };
};
export default render;
