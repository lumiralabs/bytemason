"use client";

import { ReactNode } from "react";
import NextTopLoader from "nextjs-toploader";
import { Toaster } from "react-hot-toast";
import { Tooltip } from "react-tooltip";


// All the client wrappers are here (they can't be in server components)
// 1. NextTopLoader: Show a progress bar at the top when navigating between pages
// 2. Toaster: Show Success/Error messages anywhere from the app with toast()
// 3. Tooltip: Show tooltips if any JSX elements has these 2 attributes: data-tooltip-id="tooltip" data-tooltip-content=""

const ClientLayout = ({ children }: { children: ReactNode }) => {
  return (
    <>
      <NextTopLoader color={"#000000"} showSpinner={false} />

      {/* Content inside app/page.ts files  */}
      {children}

      <Toaster
        toastOptions={{
          duration: 3000,
        }}
      />

       <Tooltip
        id="tooltip"
        className="z-[60] !opacity-100 max-w-sm shadow-lg"
      />

    </>
  );
};

export default ClientLayout;
