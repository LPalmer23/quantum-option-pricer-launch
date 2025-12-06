import React from "react";
import Plot from "react-plotly.js";

type Props = {
  histogram: { k: number; S: number; prob: number }[];
};

export default function TerminalDistributionPlot({ histogram }: Props) {
  const x = histogram.map((b) => b.S);
  const y = histogram.map((b) => b.prob);

  return (
    <div style={{ marginTop: "1.5rem" }}>
      <Plot
        data={[
          {
            x,
            y,
            type: "bar",
            marker: {
              color: "#38bdf8",
            },
          },
        ]}
        layout={{
          title: {
            text: "Quantum Terminal Price Distribution",
            font: { size: 18, color: "#e5e7eb" },
          },
          paper_bgcolor: "rgba(0,0,0,0)",
          plot_bgcolor: "rgba(0,0,0,0)",
          xaxis: {
            title: "Terminal Price (Sₖ)",
            color: "#e5e7eb",
          },
          yaxis: {
            title: "Probability",
            color: "#e5e7eb",
          },
          margin: { t: 40, l: 50, r: 20, b: 50 },
        }}
        style={{ width: "100%", height: "360px" }}
        config={{ displaylogo: false,      // hide Plotly logo, looks cleaner
        scrollZoom: true,        // keep scroll-to-zoom
        responsive: true }}
      />
    </div>
  );
}
