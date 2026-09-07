#ifndef STARPORTTRAVELSUICALLBACK_H_
#define STARPORTTRAVELSUICALLBACK_H_

#include "server/zone/ZoneServer.h"
#include "server/zone/managers/credit/CreditScale.h"
#include "server/zone/managers/planet/PlanetManager.h"
#include "server/zone/objects/player/PlayerObject.h"
#include "server/zone/objects/player/sui/SuiCallback.h"
#include "server/zone/objects/player/sui/listbox/SuiListBox.h"
#include "server/zone/objects/region/CityRegion.h"
#include "server/zone/objects/tangible/terminal/travel/TravelTerminal.h"

class StarportTravelSuiCallback : public SuiCallback {
	Reference<PlanetTravelPoint*> departure;
	Reference<PlanetTravelPoint*> arrival;
	Vector<Reference<PlanetTravelPoint*> > destinations;

public:
	StarportTravelSuiCallback(ZoneServer* server, PlanetTravelPoint* origin, PlanetTravelPoint* destination = nullptr)
		: SuiCallback(server), departure(origin), arrival(destination) {
	}

	static void showDestinations(CreatureObject* player, TravelTerminal* terminal, PlanetTravelPoint* origin) {
		auto server = player->getZoneServer();
		auto ghost = player->getPlayerObject();
		auto originZone = terminal->getZone();
		if (server == nullptr || ghost == nullptr || originZone == nullptr || !terminal->isInRange(player, 8.f))
			return;

		auto manager = originZone->getPlanetManager();
		auto box = new SuiListBox(player, SuiWindowType::STARPORT_TRAVEL_DESTINATION);
		auto callback = new StarportTravelSuiCallback(server, origin);
		box->setCallback(callback);
		box->setUsingObject(terminal);
		box->setForceCloseDistance(8.f);
		box->setPromptTitle("Travel destinations");
		box->setPromptText("Departing from " + origin->getPointName() + ". Select a destination, then choose a one-way or round-trip ticket.");
		box->setCancelButton(true, "@cancel");

		for (int i = 0; i < server->getZoneCount(); ++i) {
			auto zone = server->getZone(i);
			if (zone == nullptr || zone->getPlanetManager() == nullptr)
				continue;

			auto destinationManager = zone->getPlanetManager();
			for (int j = 0; j < destinationManager->getPlanetTravelPointCount(); ++j) {
				Reference<PlanetTravelPoint*> point = destinationManager->getPlanetTravelPointByIndex(j);
				if (point == nullptr || point == origin || !manager->isTravelToLocationPermitted(origin->getPointName(), point->getPointZone(), point->getPointName()))
					continue;

				auto shuttle = point->getShuttle();
				if (shuttle == nullptr)
					continue;

				auto city = shuttle->getCityRegion().get();
				if (city != nullptr && city->isBanned(player->getObjectID()))
					continue;

				callback->destinations.add(point);
				box->addMenuItem(point->getPointZone() + " - " + point->getPointName());
			}
		}

		ghost->addSuiBox(box);
		player->sendMessage(box->generateMessage());
	}

	void run(CreatureObject* player, SuiBox* sui, uint32 eventIndex, Vector<UnicodeString>* args) {
		if (player == nullptr || sui == nullptr || !sui->isListBox() || eventIndex != 0 || args == nullptr || args->size() == 0)
			return;

		ManagedReference<SceneObject*> terminalObject = sui->getUsingObject().get();
		auto terminal = cast<TravelTerminal*>(terminalObject.get());
		if (terminal == nullptr || !terminal->isInRange(player, 8.f) || terminal->getZone() != player->getZone())
			return;

		auto origin = terminal->getPlanetTravelPoint();
		if (origin == nullptr || origin != departure || !origin->isInterplanetary())
			return;

		auto box = cast<SuiListBox*>(sui);
		int index = Integer::valueOf(args->get(0).toString());
		if (index < 0 || index >= box->getMenuSize())
			return;

		if (arrival == nullptr) {
			if (index >= destinations.size())
				return;

			auto point = destinations.get(index);
			auto ghost = player->getPlayerObject();
			auto manager = terminal->getZone()->getPlanetManager();
			auto destinationZone = server->getZone(point->getPointZone());
			if (ghost == nullptr || destinationZone == nullptr || !manager->isTravelToLocationPermitted(origin->getPointName(), point->getPointZone(), point->getPointName()))
				return;

			int baseFare = manager->getTravelFare(origin->getPointZone(), point->getPointZone());
			if (baseFare <= 0)
				return;

			int tax = 0;
			auto city = player->getCityRegion().get();
			if (city != nullptr && !city->isClientRegion())
				tax = city->getTravelTax();

			auto tickets = new SuiListBox(player, SuiWindowType::STARPORT_TRAVEL_TICKET_TYPE);
			tickets->setCallback(new StarportTravelSuiCallback(server, origin, point));
			tickets->setUsingObject(terminal);
			tickets->setForceCloseDistance(8.f);
			tickets->setPromptTitle("Purchase travel ticket");
			tickets->setPromptText(origin->getPointName() + " to " + point->getPointName() + " (" + point->getPointZone() + "). Select a ticket to purchase, then board at this port.");
			tickets->setCancelButton(true, "@cancel");
			tickets->addMenuItem("One way - " + String::valueOf(CreditScale::credits(baseFare) + tax) + " credits", 1);
			if (destinationZone->getPlanetManager()->isTravelToLocationPermitted(point->getPointName(), origin->getPointZone(), origin->getPointName()))
				tickets->addMenuItem("Round trip - " + String::valueOf(CreditScale::credits(baseFare * 2) + tax * 2) + " credits", 2);

			ghost->addSuiBox(tickets);
			player->sendMessage(tickets->generateMessage());
			return;
		}

		String arguments = departure->getPointZone().replaceAll(" ", "_") + " " + departure->getPointName().replaceAll(" ", "_")
			+ " " + arrival->getPointZone().replaceAll(" ", "_") + " " + arrival->getPointName().replaceAll(" ", "_")
			+ (box->getMenuObjectID(index) == 1 ? " single" : " roundtrip");
		// Reuse the command's funds, inventory, coupon, city-ban and route checks.
		player->executeObjectControllerAction(STRING_HASHCODE("purchaseticket"), terminal->getObjectID(), arguments);
	}
};

#endif
