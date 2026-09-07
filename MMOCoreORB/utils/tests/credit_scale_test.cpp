#include "../../src/server/zone/managers/credit/CreditScale.h"
#include <cassert>
#include <climits>
#include <cstdint>
#include <iostream>

int main() {
	static_assert(CreditScale::credits(1000) == 10, "training price");
	static_assert(CreditScale::credits(15000) == 150, "mission reward");
	static_assert(CreditScale::credits(INT_MAX) == 21474837, "no addition overflow");
	// Lua::getGlobalInt returns uint32, so exercise the actual argument type.
	static_assert(CreditScale::credits(std::uint32_t{1000}) == 10, "unsigned Lua starting credits");
	static_assert(CreditScale::credits(std::uint32_t{101}) == 2, "unsigned rounding up");
	static_assert(CreditScale::credits(UINT32_MAX) == 42949673, "scale before converting to signed credits");
	assert(CreditScale::credits(std::uint32_t{0}) == 0);
	assert(CreditScale::credits(std::uint32_t{1}) == 1);
	assert(CreditScale::credits(std::uint32_t{99}) == 1);
	assert(CreditScale::credits(std::uint32_t{100}) == 1);
	assert(CreditScale::credits(0) == 0);
	assert(CreditScale::credits(-1) == -1);
	assert(CreditScale::credits(1) == 1);
	assert(CreditScale::credits(99) == 1);
	assert(CreditScale::credits(100) == 1);
	assert(CreditScale::credits(101) == 2);
	assert(CreditScale::credits(487) == 5);
	assert(CreditScale::credits(530) == 6);
	assert(CreditScale::credits(15001) == 151);
	assert(CreditScale::credits(100.01) == 2);
	assert(CreditScale::credits(100.01f) == 2); // Floating upkeep still selects the floating overload.
	assert(CreditScale::credits(0.01) == 1);
	assert(CreditScale::credits(0.0) == 0);
	assert(CreditScale::credits(15001.0 + 99.0) == 151);
	assert(CreditScale::credits(750 * 2) == 15); // Round-trip ticket, rounded once.
	assert(CreditScale::credits(596 + 119) == 8); // Repair including garage tax.
	assert(CreditScale::credits(3) - CreditScale::credits(1) == 0); // Already paid for the rounded stake.

	// A rounded amount is always the smallest whole credit covering the price.
	for (int amount = 1; amount <= 1000000; ++amount) {
		std::int64_t result = CreditScale::credits(amount);
		assert(result * 100 >= amount);
		assert((result - 1) * 100 < amount);
	}
	std::cout << "Credit scaling checks passed.\n";
}
