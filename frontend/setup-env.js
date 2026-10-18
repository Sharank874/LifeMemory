/**
 * Setup script to create .env.local file
 * Run: node setup-env.js
 */

const fs = require('fs');
const path = require('path');

const envContent = `# Frontend Environment Variables
# Generated automatically - do not edit manually

# Supabase Configuration - replace with your project values from Supabase dashboard
NEXT_PUBLIC_SUPABASE_URL=https://your-project-ref.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-supabase-anon-key

# Backend API URL
NEXT_PUBLIC_API_URL=http://localhost:8000
`;

const envPath = path.join(__dirname, '.env.local');

if (fs.existsSync(envPath)) {
  console.log('✅ .env.local already exists');
  console.log('   If you need to update it, edit it manually or delete and run this script again');
} else {
  fs.writeFileSync(envPath, envContent, 'utf8');
  console.log('✅ Created .env.local file');
  console.log('   Frontend environment variables are now configured');
}

console.log('\n📝 Next steps:');
console.log('   1. Make sure backend is running: cd ../backend && python main.py');
console.log('   2. Start frontend: npm run dev');
console.log('   3. Open http://localhost:3000 in your browser\n');

