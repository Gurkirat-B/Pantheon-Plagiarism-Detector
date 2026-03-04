import Link from "next/link";
// import CartButton from "./CartButton";
// import { getLoggedInMember } from "@/wix-api/members";
// import UserButton from "../UserButton";
// import { getCollections } from "@/wix-api/collections";
// import MainMenu from "./MainMenu";
// import SearchBar from "./SearchBar";
// import { fetchProducts } from "@/wix-api/products";
// import MobileMenu from "./MobileMenu";
// import { Suspense } from "react";

export default async function Navbar() {
//   const wixServerClient = await getWixServerClient();
//   const [cart, loggedInMember, collections, allProductsQuery] =
//     await Promise.all([
//       getCart(wixServerClient),
//       getLoggedInMember(wixServerClient),
//       getCollections(wixServerClient),
//       fetchProducts(wixServerClient, { sort: "lastUpdated" }),
//     ]);
//   const allProducts = allProductsQuery.items;

  return (
    <header className="bg-background shadow-sm">
      <div className="mx-auto flex max-w-7xl items-center justify-between gap-5 p-5 min-[2000px]:max-w-[2000px]">
        {/* <Suspense>
          <MobileMenu
            collections={collections}
            loggedInMember={loggedInMember}
            allProducts={allProducts}
          />
        </Suspense> */}
        <div className="flex items-center gap-5">
          <Link href="/" className="flex items-start gap-3">
            <div className="text-3xl font-semibold 2xl:text-4xl">
              <span className="text-black">Pan</span>
              <span className="text-[#d40f0d]">theon</span>
            </div>
          </Link>
          {/* <MainMenu collections={collections} className="hidden lg:flex" /> */}
        </div>
        <div className="flex items-center justify-center gap-5">
          {/* <SearchBar
            allProducts={allProducts}
            className="hidden lg:inline-flex"
          />
          <UserButton
            loggedInMember={loggedInMember}
            className="hidden lg:inline-flex"
          />
          <CartButton initialData={cart} /> */}
          <p>Test</p>
        </div>
      </div>
    </header>
  );
}
