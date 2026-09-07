#ifndef CORE3_CREDITSCALE_H
#define CORE3_CREDITSCALE_H

#include <cmath>

// Convert authored prices and generated rewards once, before displaying,
// checking or settling them. Balances, transfers and refunds use actual credits.
namespace CreditScale {

constexpr int DIVISOR = 100;

constexpr int credits(int amount) {
	// Preserve zero and negative sentinel values; avoid overflow from amount + 99.
	return amount <= 0 ? amount : amount / DIVISOR + (amount % DIVISOR != 0);
}

inline int credits(double amount) {
	return amount <= 0 ? static_cast<int>(amount) : static_cast<int>(std::ceil(amount / DIVISOR));
}

} // namespace CreditScale

#endif
