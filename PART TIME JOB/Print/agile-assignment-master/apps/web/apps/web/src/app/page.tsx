import MediaSelectionButton from "@/components/MediaSelectionButton";

export default function Home() {
  return (
    <main style={{ padding: "2rem", fontFamily: "system-ui, sans-serif" }}>
      <h1 style={{ fontSize: "1.25rem", fontWeight: 600, marginBottom: "1.5rem" }}>
        Agile Assignment
      </h1>

      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: "8px",
          padding: "10px 12px",
          border: "1.5px solid #e5e7eb",
          borderRadius: "12px",
          maxWidth: "640px",
          background: "#fff",
        }}
      >
        <MediaSelectionButton />
        <input
          type="text"
          placeholder="Type a message…"
          style={{
            flex: 1,
            border: "none",
            outline: "none",
            fontSize: "14px",
            background: "transparent",
          }}
        />
      </div>
    </main>
  );
}