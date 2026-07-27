import { render, screen } from '@testing-library/react';
import App from './App';

test('renders the AutoVend home page', () => {
  render(<App />);
  expect(screen.getByText('AUTOVEND')).toBeInTheDocument();
  expect(screen.getByRole('button', { name: /start the demo/i })).toBeInTheDocument();
});
