-- Run from the repository root: lua MMOCoreORB/utils/tests/credit_economy_test.lua
-- Exercise production screenplay methods with a small in-memory game interface.
local scripts = "MMOCoreORB/bin/scripts/screenplays/"
local function equal(actual, expected, label)
	assert(actual == expected, label .. ": expected " .. tostring(expected) .. ", got " .. tostring(actual))
end

ScreenPlay = { new = function(_, object) return object end }
conv_handler = ScreenPlay
registerScreenPlay = function() end
includeFile = function() end
writeData = function() end
deleteData = function() end
getStringId = function(value) return value end
printLuaError = error
CreatureObject = function(value) return value end
SceneObject = CreatureObject
ShipObject = CreatureObject
LuaSkill = CreatureObject
LuaConversationScreen = CreatureObject
LuaConversationTemplate = CreatureObject
PlayerObject = CreatureObject
package.loaded["screenplays.screenplay"] = {}
package.loaded["managers.object.object_manager"] = {}

local screen = {
	cloneScreen = function(self) return self end,
	setDialogTextStringId = function() end,
	setDialogTextDI = function(self, value) self.quote = value end,
	setDialogTextTO = function() end,
	addOption = function() end,
}
local template = { getScreen = function() return screen end }
LuaStringIdChatParameter = function(id)
	return {
		id = id,
		setDI = function(self, value) self.amount = value end,
		setTO = function() end,
		_getObject = function(self) return self end,
	}
end
local function player(cash, bank, persuasion)
	return {
		cash = cash, bank = bank, persuasion = persuasion or 0, messages = {},
		getCashCredits = function(self) return self.cash end,
		getBankCredits = function(self) return self.bank end,
		getSkillMod = function(self) return self.persuasion end,
		getObjectID = function() return 1 end,
		getFirstName = function() return "Tester" end,
		getPlayerObject = function() return nil end,
		subtractCashCredits = function(self, amount)
			assert(amount >= 0 and amount % 1 == 0 and amount <= self.cash)
			self.cash = self.cash - amount
		end,
		subtractBankCredits = function(self, amount)
			assert(amount >= 0 and amount % 1 == 0 and amount <= self.bank)
			self.bank = self.bank - amount
		end,
		addCashCredits = function(self, amount)
			assert(amount >= 0 and amount % 1 == 0)
			self.cash = self.cash + amount
		end,
		sendSystemMessage = function(self, message) table.insert(self.messages, message) end,
		sendSystemMessageWithDI = function(self, id, amount) table.insert(self.messages, { id = id, amount = amount }) end,
	}
end

local authoredPrice = 1000
local skill = { getMoneyRequired = function() return authoredPrice end }
local awarded = false
LuaSkillManager = function()
	return {
		getSkill = function() return skill end,
		canLearnSkill = function() return true end,
		awardSkill = function() awarded = true; return true end,
	}
end
SkillTrainer = { hasSurpassedTrainer = function() return false end }
dofile(scripts .. "trainers/trainerConvHandler.lua")
-- This method only redirects the conversation on a failed funds/skill check.
trainerConvHandler.runScreenHandlers = function() return screen end

local function train(price, cash, bank, persuasion, expected, shouldSucceed)
	authoredPrice, awarded = price, false
	local p = player(cash, bank, persuasion)
	trainerConvHandler:handleLearnScreen(template, p, {}, 0, screen, "marksman", "@skill_teacher:", {"pistol_1"}, 1)
	equal(screen.quote, expected, "training quote")
	trainerConvHandler:handleConfirmLearnScreen(template, p, {}, 0, screen, "marksman", "@skill_teacher:", {"pistol_1"}, 1)
	equal(awarded, shouldSucceed, "training authorization")
	equal(p.cash + p.bank, cash + bank - (shouldSucceed and expected or 0), "total charged")
	if shouldSucceed then equal(p.messages[1].amount, expected, "receipt") end
	return p
end
train(1000, 10, 0, 0, 10, true)
local split = train(1000, 3, 7, 0, 10, true)
equal(split.cash, 0, "cash portion")
equal(split.bank, 0, "bank portion")
train(1000, 3, 6, 0, 10, false)
train(1001, 0, 11, 0, 11, true)
train(1001, 0, 10, 0, 11, false)
train(1001, 20, 0, 25, 8, true)
train(99, 1, 0, 0, 1, true)
train(0, 0, 0, 0, 0, true)

dofile(scripts .. "trainers/skillTrainer.lua")
local infoRows = {}
SuiListBox = { new = function()
	return {
		setTitle = function() end, setPrompt = function() end,
		setTargetNetworkId = function() end, setForceCloseDistance = function() end,
		add = function(text) table.insert(infoRows, text) end,
		sendTo = function() end,
	}
end }
skill.getSkillPointsRequired = function() return 3 end
skill.getSkillsRequired = function() return nil end
skill.getXpCost = function() return 1000 end
skill.getXpType = function() return "combat_pistol" end
authoredPrice = 1001
local trainee = player(20, 0, 25)
SkillTrainer:sendSkillInfoSui(trainee, trainee, "pistol_1")
equal(infoRows[2], " 8 credits", "skill information price matches discounted training quote")
equal(infoRows[4], " 3 points", "skill point cost unaffected")
equal(infoRows[#infoRows], " @exp_n:combat_pistol = 1000", "XP cost unaffected")

dofile(scripts .. "themepark/themeParkLogic.lua")
for _, case in ipairs({{15000, 150}, {15001, 151}, {1, 1}, {0, 0}}) do
	local p = player(0, 0)
	ThemeParkLogic:giveCredits(p, case[1])
	equal(p.cash, case[2], "quest payment")
	equal(p.messages[1].amount, case[2], "quest reward message")
end

dofile(scripts .. "space/spacestations/spacestation.lua")
local ship = {getObjectName = function() return "xwing" end, getTotalShipDamage = function() return 1001 end}
equal(SpaceStationScreenPlay:getRepairCost(ship, 1), 11, "full ship repair")
equal(SpaceStationScreenPlay:getRepairCost(ship, 0.5), 5, "partial ship repair")
equal(SpaceStationScreenPlay:hasCreditsForRepair(player(10, 0), ship, 1), false, "repair affordability")
equal(SpaceStationScreenPlay:hasCreditsForRepair(player(11, 0), ship, 1), true, "repair at exact price")
equal(SpaceStationScreenPlay:getRepairCost(nil, 1), 0, "missing ship")

print("Credit economy screenplay checks passed.")
