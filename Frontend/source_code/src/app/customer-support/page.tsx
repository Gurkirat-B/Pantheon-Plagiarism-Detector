export default async function CustomerSupportPage() {
    const res = await fetch(
        `${process.env.BACKEND_URL}/assignments/`,
        {
          headers: {
            Accept: "application/json",
          },
          cache: "no-store",
        },
      );

      if (!res.ok) throw new Error("Interal Server Error");
    return (
        <div className="mx-auto max-w-7xl px-8 py-14 min-[2000px]:max-w-[2000px]">
            <h1>Customer Support</h1>
            <p>Welcome to our customer support page!</p>
        </div>
    )
}