export async function mockDelay<T>(payload: T): Promise<T> {
  return Promise.resolve(payload);
}
