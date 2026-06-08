# La Mia Cucina

A mobile-first Italian recipe app — save recipes, plan your week, and build your shopping list.

**Live:** https://federicamessi2000.github.io/la-mia-cucina/

---

## Features

- **Ricette** — Browse shared recipes, filter by "della mamma" or from the web, search by name, view with scalable portions
- **Aggiungi** — Add recipes manually with structured ingredients, or import automatically from any recipe website using AI
- **Planner** — Monthly meal planner (lunch + dinner), private per account, auto-populates the shopping list
- **Spesa** — Shopping list with items from the planner, from recipe buttons, and manual additions

## Stack

- Vanilla HTML/CSS/JS — single `index.html`, no build step
- Firebase Realtime Database + Google Auth
- Claude AI for recipe extraction from URLs
- PWA — installable on mobile

## Setup

The app uses Firebase and is designed to be opened directly as an `index.html` file (or served via GitHub Pages). No installation or build step required.

Sign in with Google to access your private planner and shopping list. Recipes are shared across all users.

## Notes

- Recipes tagged **Mamma** are family recipes; recipes tagged **Web** are from the internet
- The AI import feature fetches the page, extracts the recipe text, and uses Claude to structure it as JSON
- Your planner and shopping list are private — only you can see them
