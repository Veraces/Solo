/*
				Copyright <SWGEmu>
		See file COPYING for copying conditions.*/

#ifndef TUMBLETOSTANDINGCOMMAND_H_
#define TUMBLETOSTANDINGCOMMAND_H_

class TumbleToStandingCommand : public QueueCommand {
public:

	TumbleToStandingCommand(const String& name, ZoneProcessServer* server)
		: QueueCommand(name, server) {

	}

	int doQueueCommand(CreatureObject* creature, const uint64& target, const UnicodeString& arguments) const {

		if (!checkStateMask(creature))
			return INVALIDSTATE;

		if (!checkInvalidLocomotions(creature))
			return INVALIDLOCOMOTION;

		// A successful tumble consumes all remaining primary HAM pools.
		if (creature->getHAM(CreatureAttribute::HEALTH) <= 0
				|| creature->getHAM(CreatureAttribute::ACTION) <= 0
				|| creature->getHAM(CreatureAttribute::MIND) <= 0)
			return INSUFFICIENTHAM;

		creature->setPosture(CreaturePosture::UPRIGHT, false, true);

		Reference<CreatureObject*> defender = server->getZoneServer()->getObject(target).castTo<CreatureObject*>();
		if (defender == nullptr)
			creature->doCombatAnimation(creature,STRING_HASHCODE("tumble"),0,0xFF);
		else
			creature->doCombatAnimation(defender,STRING_HASHCODE("tumble_facing"),0,0xFF);

		if (creature->isDizzied() && System::random(100) < 85) {
			creature->queueDizzyFallEvent();
		} else {
			Reference<StateBuff*> buff = new StateBuff(creature, CreatureState::TUMBLING, 1);

			Locker locker(buff);

			buff->setSkillModifier("melee_defense", 50);
			buff->setSkillModifier("ranged_defense", 50);

			creature->addBuff(buff);

			locker.release();

			creature->sendStateCombatSpam("cbt_spam", "tum_standing", 0);
		}

		// Finish the tumble before incapacitating. Damage calls would stop
		// after the first empty pool, so update all three and notify once.
		creature->clearDizzyEvent();
		creature->setHAM(CreatureAttribute::HEALTH, 0, true);
		creature->setHAM(CreatureAttribute::ACTION, 0, true);
		creature->setHAM(CreatureAttribute::MIND, 0, true);
		creature->notifyObjectDestructionObservers(creature, 0, false);

		return SUCCESS;
	}

};

#endif //TUMBLETOSTANDINGCOMMAND_H_
