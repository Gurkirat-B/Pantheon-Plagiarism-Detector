import { OpenGraph } from "next/dist/lib/metadata/types/opengraph-types";

export const openGraphShared: OpenGraph = {
  siteName: "Pantheon",
  type: "website",
  images: [
    {
        type: "image/png",
        width: 1200,
        height: 630,
        url: "/opengraph-image.png",
        alt: "Pantheon Slogan"
    }
  ]
};
