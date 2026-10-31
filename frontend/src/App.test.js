import { render, screen } from '@testing-library/react';
import App from './App';

test('renders the AutoVend home page', () => {
  render(<App />);
  expect(screen.getByText('AUTO')).toBeInTheDocument();
  expect(screen.getByText('VEND')).toBeInTheDocument();
  expect(screen.getByRole('button', { name: /start demo experience/i })).toBeInTheDocument();
});
