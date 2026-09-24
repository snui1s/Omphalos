/** Creates a counter closure. */
export function createCounter() {
    let count = 0;
    return () => ++count;
}

const internalHelper = () => 42;
