/* Local UI translations. No DOM rewriting, network requests or user text processing. */
const __claudeGatewayZh = __CATALOG__;
const __claudeGatewayZhCache = new WeakMap();
function __claudeGatewayZhOverlay(original) {
  if (!original || typeof original !== 'object') original = {};
  const cached = __claudeGatewayZhCache.get(original);
  if (cached) return cached;
  const owns = key => typeof key === 'string' && Object.prototype.hasOwnProperty.call(__claudeGatewayZh, key);
  // Use a fresh extensible target so frozen upstream proxies cannot violate Proxy invariants.
  const translated = new Proxy(Object.create(null), {
    get(_target, key) { return owns(key) ? __claudeGatewayZh[key] : Reflect.get(original, key); },
    has(_target, key) { return owns(key) || Reflect.has(original, key); },
    ownKeys() { return [...new Set([...Reflect.ownKeys(original), ...Object.keys(__claudeGatewayZh)])]; },
    getOwnPropertyDescriptor(_target, key) {
      if (owns(key)) return {value: __claudeGatewayZh[key], writable: false, enumerable: true, configurable: true};
      const descriptor = Reflect.getOwnPropertyDescriptor(original, key);
      return descriptor ? {...descriptor, configurable: true} : undefined;
    }
  });
  __claudeGatewayZhCache.set(original, translated);
  return translated;
}
