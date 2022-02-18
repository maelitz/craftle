let recipes;
let tags;
let targetRecipe;
let ingredients;
let selectedIngredient = null;
let craftingInputs;
let craftingOutput;
let attempts;
const MAX_ATTEMPTS = 27;

function mulberry32(a) {
    return function() {
		let t = a += 0x6D2B79F5;
		t = Math.imul(t ^ t >>> 15, t | 1);
		t ^= t + Math.imul(t ^ t >>> 7, t | 61);
		return ((t ^ t >>> 14) >>> 0) / 4294967296;
    }
}

function initDaily() {
	const today = new Date();
	const dayNumber = (today.getFullYear() - 2000) * 365 + today.getMonth() * 12 + (today.getDate() - 1);
	const rng = mulberry32(dayNumber);
	targetRecipe = recipes[Math.floor(rng() * recipes.length)];
}

function initRandom() {
	targetRecipe = recipes[Math.floor(Math.random() * recipes.length)];
}

function initIngredients() {
	let ingredientsDiv = document.getElementById('ingredients');
	while (ingredients.firstChild)
		ingredients.removeChild(ingredients.firstChild);
	for (let ingredient of ingredients) {
		let ingredientDiv = document.createElement('div');
		let ingredientId = ingredient.replace(':', '/');
		ingredientDiv.classList.add('ingredient');
		ingredientDiv.style.backgroundImage = `url("img/${ingredientId}.png")`;
		ingredientsDiv.appendChild(ingredientDiv);
		ingredientDiv.addEventListener('click', () => {
			selectedIngredient = ingredient;
		});
	}
}

function initCraftingTable() {
	craftingInputs = new Array(9).fill(null);
	craftingOutput = null;
	attempts = 0;
	for (let [i, ingredientInput] of Object.entries(document.querySelectorAll('#crafting-input .ingredient'))) {
		ingredientInput.addEventListener('click', () => {
			craftingInputs[i] = selectedIngredient;
			if (selectedIngredient) {
				let ingredientId = selectedIngredient.replace(':', '/');
				ingredientInput.style.backgroundImage = `url("img/${ingredientId}.png")`;
			} else {
				ingredientInput.style.backgroundImage = '';
			}
			selectedIngredient = null;
			updateCraftingOutput();
		});
	}
	const craftingOutputDiv = document.getElementById('crafting-output');
	craftingOutputDiv.addEventListener('click', () => {
		if (craftingOutput !== null) {
			let ingredientId = craftingOutput.replace(':', '/');
			const inventoryDiv = document.querySelectorAll('#crafting-inventory .ingredient')[attempts];
			inventoryDiv.style.backgroundImage = `url("img/${ingredientId}.png")`;
			handleCraftingAttempt();
		}
	});
}

function handleCraftingAttempt() {
	++attempts;
	if (checkExactRecipe(targetRecipe)) {
		alert('success');
	} else if (attempts === MAX_ATTEMPTS) {
		alert('fail');
	}
}

function updateCraftingOutput() {
	const craftingOutputDiv = document.getElementById('crafting-output');
	for (let recipe of recipes) {
		if (checkExactRecipe(recipe)) {
			craftingOutput = recipe.result.item;
			let ingredientId = craftingOutput.replace(':', '/');
			craftingOutputDiv.style.backgroundImage = `url("img/${ingredientId}.png")`;
			return;
		}
	}
	craftingOutput = null;
	craftingOutputDiv.style.backgroundImage = '';
}

function checkExactShapelessRecipe(recipe) {
	const remainingInputs = [...craftingInputs];
	for (let ingredientChoices of recipe.ingredients) {
		let found = false;
		for (let ingredientChoice of expandIngredientChoices(ingredientChoices)) {
			if (remainingInputs.includes(ingredientChoice)) {
				remainingInputs[remainingInputs.indexOf(ingredientChoice)] = null;
				found = true;
				break;
			}
		}
		if (!found)
			return false;
	}
	for (let remainingInput of remainingInputs)
		if (remainingInput !== null)
			return false;
	return true;
}

function expandIngredientChoices(ingredientChoices) {
	let res = [];
	if (!Array.isArray(ingredientChoices))
		ingredientChoices = [ingredientChoices];
	for (let ingredientChoice of ingredientChoices) {
		if (ingredientChoice.tag)
			res.push(...tags[ingredientChoice.tag.replace('minecraft:', '')].values);
		else
			res.push(ingredientChoice.item);
	}
	while (res.some(s => s.startsWith('#'))) {
		res = res.reduce((r, e) => {
			if (e.startsWith('#'))
				r.push(...tags[e.replace('#minecraft:', '')].values);
			else
				r.push(e);
			return r;
		}, []);
	}
	for (let expandedElement of res) {
		if (expandedElement.startsWith('#'))
			console.log(ingredientChoices, expandedElement);
	}
	return res;
}

function flattenCraftingPattern(pattern, rowOffset, colOffset) {
	const res = new Array(9).fill(null);
	for (let [rowNumber, row] of pattern.entries()) {
		for (let [colNumber, key] of row.split('').entries()) {
			res[(rowNumber + rowOffset) * 3 + colNumber + colOffset] = (key !== ' ') ? key : null;
		}
	}
	return res;
}

function checkExactShapedRecipe(recipe) {
	let nRows = recipe.pattern.length;
	let nCols = Math.max(...recipe.pattern.map(e => e.length));
	for (let rowOffset = 0; rowOffset < (4 - nRows); ++rowOffset) {
		for (let colOffset = 0; colOffset < (4 - nCols); ++colOffset) {
			let correct = true;
			const flatPattern = flattenCraftingPattern(recipe.pattern, rowOffset, colOffset);
			for (let i = 0; i < 9; ++i) {
				if ((flatPattern[i] === null) !== (craftingInputs[i] === null)) {
					correct = false;
					break;
				}
				if (flatPattern[i] !== null) {
					let ingredientChoices = recipe.key[flatPattern[i]];
					if (!expandIngredientChoices(ingredientChoices).includes(craftingInputs[i])) {
						correct = false;
						break;
					}
				}
			}
			if (correct)
				return true;
		}
	}
	return false;
}

function checkExactRecipe(recipe) {
	if (recipe.type === 'minecraft:crafting_shapeless')
		return checkExactShapelessRecipe(recipe);
	if (recipe.type === 'minecraft:crafting_shaped')
		return checkExactShapedRecipe(recipe);
	return false;
}

document.addEventListener('DOMContentLoaded', () => {
	const fetchRecipes = fetch('recipes.json').then(r => r.json()).then(r =>
		recipes = r.filter(e => ['minecraft:crafting_shaped', 'minecraft:crafting_shapeless'].includes(e.type)));
	const fetchTags = fetch('tags.json').then(r => r.json()).then(r => tags = r);
	Promise.all([fetchRecipes, fetchTags]).then(() => {
		ingredients = new Set();
		for (let recipe of recipes) {
			let recipeIngredients;
			if (recipe.type === 'minecraft:crafting_shaped')
				recipeIngredients = Object.entries(recipe.key).map(([key, ingredient]) => ingredient);
			else
				recipeIngredients = recipe.ingredients;
			for (let ingredientChoices of recipeIngredients) {
				for (let ingredientChoice of expandIngredientChoices(ingredientChoices))
					ingredients.add(ingredientChoice);
			}
		}
		ingredients = Array.from(ingredients).sort();
		initIngredients();
		initCraftingTable();
		initDaily();
		document.getElementById('start-random').addEventListener('click', initRandom);
	});
});
