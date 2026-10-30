export type ReleaseVersion = "v1" | "v2";

export interface ProductItem {
  sku: string;
  name: string;
  price: string;
  spec: string;
}

export interface ScenarioSpec {
  id: string;
  title: string;
  v1Selector: string;
  intent: string;
  expectedBanner: string;
  hasTargetInV2: boolean;
}