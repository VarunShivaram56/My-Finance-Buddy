module.exports = {
  content: ["./src/**/*.{js,jsx,ts,tsx}", "./public/index.html"],
  theme: {
    extend: {
      colors: {
        skywash: "#fff1df",
        mist: "#fff9f2",
        ink: "#7a3d1c",
        slateBlue: "#e8a15b",
        borderSoft: "#f2d6ba",
        saffronSoft: "#f9c68b",
        clay: "#c26c32",
        leaf: "#8f9b57",
      },
      boxShadow: {
        soft: "0 18px 42px rgba(184, 112, 53, 0.12)",
      },
      animation: {
        float: "float 6s ease-in-out infinite",
      },
      keyframes: {
        float: {
          "0%, 100%": { transform: "translateY(0px)" },
          "50%": { transform: "translateY(-10px)" },
        },
      },
    },
  },
  plugins: [],
};
