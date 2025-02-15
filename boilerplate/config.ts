import { ConfigProps } from "./types/config";

const config = {
  appName: "",
  appDescription: "",
  domainName: "",

  auth: {
    loginUrl: "/signin",
    callbackUrl: "/dashboard",
  },

  theme: {
    primary: "#f37055",
  }
} as ConfigProps;

export default config;
