import type { Broadcast } from '../types';

export const broadcastStatusVariant: Record<Broadcast['status'], 'gray' | 'yellow' | 'green' | 'red' | 'blue'> = {
  draft: 'gray',
  scheduled: 'yellow',
  sending: 'blue',
  sent: 'green',
  cancelled: 'gray',
  failed: 'red',
};
