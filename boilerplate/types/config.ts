
export interface ConfigProps {
  appName: string;
  appDescription: string;
  domainName: string;
  
  auth: {
    loginUrl: string;
    callbackUrl: string;
  };

  theme: {
    primary: string;
  };
}
