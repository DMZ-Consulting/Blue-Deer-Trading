# Blue Deer Trading Frontend

A Next.js frontend application for the Blue Deer Trading platform.

## Setup

1. Install dependencies:
```bash
npm install
```

2. Create a `.env.local` file in the root directory with your Supabase credentials:
```
NEXT_PUBLIC_SUPABASE_URL=your-supabase-url
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-supabase-anon-key
```

3. Run the development server:
```bash
npm run dev
```

## Project Structure

- `/src/components`: React components
- `/src/api`: API client and utilities
- `/lib`: Shared utilities and types
  - `database.types.ts`: TypeScript types for the database schema
  - `portfolio.ts`: Portfolio calculation utilities
  - `supabase.ts`: Supabase client and queries

## Features

- Real-time trade tracking
- Portfolio statistics
- Monthly P/L visualization
- Trade configuration management

## Database Schema

The application uses Supabase as its database with the following tables:

- `trades`: Individual trade records
- `options_strategy_trades`: Options strategy trade records
- `transactions`: Trade transactions
- `options_strategy_transactions`: Options strategy transactions
- `trade_configurations`: Trade configuration settings

## Development

1. Make sure you have the latest dependencies installed:
```bash
npm install
```

2. Start the development server:
```bash
npm run dev
```

3. Open [http://localhost:3000](http://localhost:3000) in your browser.

## Building for Production

1. Build the application:
```bash
npm run build
```

2. Start the production server:
```bash
npm start
```

## Environment Variables

- `NEXT_PUBLIC_SUPABASE_URL`: Your Supabase project URL
- `NEXT_PUBLIC_SUPABASE_ANON_KEY`: Your Supabase anonymous key

## Contributing

1. Create a new branch for your feature
2. Make your changes
3. Submit a pull request

## License

MIT
