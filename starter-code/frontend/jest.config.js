module.exports = {
  preset: 'ts-jest',
  testEnvironment: 'jsdom',
  
  // Tests are now inside src/tests
  roots: [
    '<rootDir>/src/tests',
    '<rootDir>/src'
  ],
  
  // Base URL for imports
  modulePaths: ['<rootDir>/src'],
  
  moduleNameMapper: {
    // Mock CSS imports
    '\\.(css|less|scss|sass)$': 'identity-obj-proxy',
    
    // Path aliases matching tsconfig
    '^components/(.*)$': '<rootDir>/src/components/$1',
    '^hooks/(.*)$': '<rootDir>/src/hooks/$1',
    '^utils/(.*)$': '<rootDir>/src/utils/$1',
    '^types/(.*)$': '<rootDir>/src/types/$1',
    '^context/(.*)$': '<rootDir>/src/context/$1',
    '^@/(.*)$': '<rootDir>/src/$1',
  },
  
  // Setup file
  setupFilesAfterEnv: ['<rootDir>/src/tests/setupTests.ts'],
  
  // Transform TypeScript
  transform: {
    '^.+\\.tsx?$': ['ts-jest', {
      tsconfig: {
        jsx: 'react-jsx',
        esModuleInterop: true,
        allowSyntheticDefaultImports: true,
      },
    }],
  },
  
  // Test file patterns
  testMatch: [
    '<rootDir>/src/tests/**/*.test.ts',
    '<rootDir>/src/tests/**/*.test.tsx',
  ],
  
  // Coverage
  collectCoverageFrom: [
    'src/**/*.{ts,tsx}',
    '!src/**/*.d.ts',
    '!src/index.tsx',
    '!src/reportWebVitals.ts',
    '!src/tests/**/*',
  ],
  
  moduleFileExtensions: ['ts', 'tsx', 'js', 'jsx', 'json'],
};