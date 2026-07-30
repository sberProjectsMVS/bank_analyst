import fs from "node:fs/promises";
import https from "node:https";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const outputDir =
  "/Users/ilyashmarov/Documents/analyst/bank_analyst/outputs/sber_premier_foreign_lounges_2026-07-28";
const apiBase = "https://mir.pass.nspk.ru/sber-pass/api/v1/typeReference";
const checkedAt = new Date(2026, 6, 28);
const checkedAtText = "2026-07-28";
const dateTime = "2026-07-28T12:00";

function fetchJson(url) {
  return new Promise((resolve, reject) => {
    const request = https.get(
      url,
      {
        rejectUnauthorized: false,
        headers: {
          Accept: "application/json",
          Referer: "https://mir.pass.nspk.ru/sber/ru",
          "User-Agent":
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/138 Safari/537.36",
        },
      },
      (response) => {
        let body = "";
        response.setEncoding("utf8");
        response.on("data", (chunk) => {
          body += chunk;
        });
        response.on("end", () => {
          if (response.statusCode !== 200) {
            reject(
              new Error(
                `HTTP ${response.statusCode} for ${url}: ${body.slice(0, 300)}`,
              ),
            );
            return;
          }
          resolve(JSON.parse(body));
        });
      },
    );
    request.on("error", reject);
  });
}

function loungeUrl(item) {
  const params = new URLSearchParams({
    airportCode: item.airportCode.trim(),
    loungeId: String(item.loungeId),
    package: "programm7",
  });
  return `https://mir.pass.nspk.ru/sber/ru/lounges?${params.toString()}`;
}

function normalizedCountry(item) {
  const code = item.countryCode.trim();
  const byCode = {
    ARE: "Объединённые Арабские Эмираты",
    UAE: "Объединённые Арабские Эмираты",
    ARM: "Армения",
    BLR: "Беларусь",
    KGZ: "Кыргызстан",
    USA: "США",
  };
  return byCode[code] ?? item.countryName;
}

const commonParams = new URLSearchParams({
  locale: "ru",
  dateTime,
  productId: "programm7",
});
const level3Url = `${apiBase}/loungeList?${commonParams.toString()}`;
const productListUrl = `${apiBase}/productList?locale=ru`;
const hashUrl = `${apiBase}/loungeHash?locale=ru`;

const [catalog, products, hashInfo] = await Promise.all([
  fetchJson(level3Url),
  fetchJson(productListUrl),
  fetchJson(hashUrl),
]);

const level2 = products.find((item) => item.productId === "programm6");
const level3 = products.find((item) => item.productId === "programm7");
if (!level2 || !level3 || level2.isRussia !== true || level3.isRussia !== false) {
  throw new Error("Официальная география уровней 2 и 3 изменилась");
}

const foreignLounges = catalog
  .filter((item) => item.countryCode.trim() !== "RUS")
  .sort((left, right) =>
    [
      normalizedCountry(left).localeCompare(normalizedCountry(right), "ru"),
      left.cityName.localeCompare(right.cityName, "ru"),
      left.airportName.localeCompare(right.airportName, "ru"),
      left.loungeName.localeCompare(right.loungeName, "ru"),
    ].find((value) => value !== 0) ?? 0,
  );

if (!foreignLounges.length) {
  throw new Error("Зарубежные бизнес-залы уровня 3 не найдены");
}

const countryCount = new Set(foreignLounges.map(normalizedCountry)).size;
const cityCount = new Set(
  foreignLounges.map((item) => `${normalizedCountry(item)}|${item.cityName}`),
).size;
const nodeCount = new Set(
  foreignLounges.map((item) => `${item.countryCode.trim()}|${item.airportCode.trim()}`),
).size;
const openCount = foreignLounges.filter((item) => !item.isClosed).length;
const closedCount = foreignLounges.filter((item) => item.isClosed).length;

const nodeTypes = {
  1: "Аэропорт",
  2: "Ж/д вокзал",
  3: "Морской порт",
};
const flightTypes = {
  0: "Внутренний",
  1: "Международный",
  2: "Все рейсы",
  3: "Не применяется",
};
const serviceTypes = {
  onpass: "ON·PASS",
  onpass_premium: "ON·PASS Premium",
};

const workbook = Workbook.create();
const summary = workbook.worksheets.add("Сводка");
const data = workbook.worksheets.add("Зарубежные залы");
summary.showGridLines = false;
data.showGridLines = false;

summary.getRange("A1:H1").merge();
summary.getRange("A1").values = [
  ["Зарубежные бизнес-залы СберПремьер"],
];
summary.getRange("A2:H2").merge();
summary.getRange("A2").values = [
  [
    "Официальный перечень для 2-го и 3-го уровней. Срез на 28 июля 2026 года.",
  ],
];

summary.getRange("A4:A9").values = [
  ["Зарубежных залов"],
  ["Открыты"],
  ["Временно закрыты"],
  ["Стран"],
  ["Городов"],
  ["Аэропортов"],
];
const dataLastRow = foreignLounges.length + 1;
summary.getRange("B4").formulas = [
  [`=COUNTA('Зарубежные залы'!A2:A${dataLastRow})`],
];
summary.getRange("B5").formulas = [
  [`=COUNTIF('Зарубежные залы'!P2:P${dataLastRow},"Открыт")`],
];
summary.getRange("B6").formulas = [
  [`=COUNTIF('Зарубежные залы'!P2:P${dataLastRow},"Временно закрыт")`],
];
summary.getRange("B7:B9").values = [[countryCount], [cityCount], [nodeCount]];

summary.getRange("D4:F9").values = [
  ["Показатель", "Уровень 2", "Уровень 3"],
  ["География", "Только Россия", "Россия и зарубежье"],
  ["Зарубежные залы", 0, foreignLounges.length],
  ["Зарубежные страны", 0, countryCount],
  ["Сервис за рубежом", "—", "ON·PASS"],
  ["Проверено", checkedAt, checkedAt],
];
summary.getRange("E9:F9").format.numberFormat = "yyyy-mm-dd";

summary.getRange("A11:H11").merge();
summary.getRange("A11").values = [["Что важно"]];
summary.getRange("A12:H12").merge();
summary.getRange("A12").values = [
  [
    "Зарубежные бизнес-залы подтверждены только для СберПремьера 3-го уровня. В официальном каталоге уровень 2 помечен как «только Россия», уровень 3 — как «залы по всему миру (и Россия тоже)».",
  ],
];
summary.getRange("A13:H13").merge();
summary.getRange("A13").values = [
  [
    `В зарубежной части каталога ${foreignLounges.length} позиции: ${openCount} открыты, ${closedCount} временно закрыты. Закрытые позиции сохранены в таблице и выделены цветом.`,
  ],
];
summary.getRange("A14:H14").merge();
summary.getRange("A14").values = [
  [
    `Каталог оператора обновлён ${String(hashInfo.updateDate).slice(0, 10)}; проверка выполнена ${checkedAtText}. ОАЭ представлены в API двумя кодами (ARE и UAE), но в сводке считаются одной страной.`,
  ],
];

summary.getRange("A16:H16").merge();
summary.getRange("A16").values = [["Официальные источники"]];
summary.getRange("A17:H17").merge();
summary.getRange("A17").values = [["https://mir.pass.nspk.ru/sber/ru"]];
summary.getRange("A18:H18").merge();
summary.getRange("A18").values = [[productListUrl]];
summary.getRange("A19:H19").merge();
summary.getRange("A19").values = [[level3Url]];

summary.getRange("A1:H1").format = {
  fill: "#0F6B45",
  font: { bold: true, color: "#FFFFFF", size: 20 },
  verticalAlignment: "center",
};
summary.getRange("A1:H1").format.rowHeight = 34;
summary.getRange("A2:H2").format = {
  fill: "#EAF5EF",
  font: { color: "#244737", size: 11 },
  verticalAlignment: "center",
};
summary.getRange("A2:H2").format.rowHeight = 28;
summary.getRange("A4:A9").format = {
  fill: "#F3F6F4",
  font: { bold: true, color: "#52645A" },
};
summary.getRange("B4:B9").format = {
  fill: "#FFFFFF",
  font: { bold: true, color: "#16251D", size: 16 },
  horizontalAlignment: "center",
};
summary.getRange("A4:B9").format.borders = {
  preset: "outside",
  style: "thin",
  color: "#C8D8CF",
};
summary.getRange("D4:F9").format.borders = {
  preset: "outside",
  style: "thin",
  color: "#C8D8CF",
};
summary.getRange("D4:F4").format = {
  fill: "#0F6B45",
  font: { bold: true, color: "#FFFFFF" },
  horizontalAlignment: "center",
};
summary.getRange("D5:D9").format = {
  fill: "#F3F6F4",
  font: { bold: true, color: "#52645A" },
};
summary.getRange("E5:F9").format = {
  fill: "#FFFFFF",
  horizontalAlignment: "center",
};
summary.getRange("A11:H11").format = {
  fill: "#DDEEE5",
  font: { bold: true, color: "#0F6B45", size: 13 },
};
summary.getRange("A12:H14").format = {
  fill: "#F8FBF9",
  font: { color: "#27382F" },
  wrapText: true,
  verticalAlignment: "center",
};
summary.getRange("A12:H14").format.rowHeight = 38;
summary.getRange("A16:H16").format = {
  fill: "#DDEEE5",
  font: { bold: true, color: "#0F6B45", size: 13 },
};
summary.getRange("A17:H19").format = {
  font: { color: "#176F48", underline: true },
  wrapText: true,
};
summary.getRange("A1:H19").format.columnWidth = 13;
summary.getRange("A1:A19").format.columnWidth = 21;
summary.getRange("B1:B19").format.columnWidth = 14;
summary.getRange("C1:C19").format.columnWidth = 3;
summary.getRange("D1:D19").format.columnWidth = 20;
summary.getRange("E1:F19").format.columnWidth = 20;

const headers = [
  "№",
  "Страна",
  "Код страны API",
  "Город",
  "Код узла",
  "Аэропорт / транспортный узел",
  "Тип узла",
  "Бизнес-зал",
  "Терминал",
  "Этаж",
  "Тип рейса",
  "Сервис",
  "Режим работы",
  "Адрес",
  "Уровни",
  "Статус",
  "ID",
  "Официальная карточка",
  "Проверено",
];
data.getRange("A1:S1").values = [headers];
const rows = foreignLounges.map((item, index) => [
  index + 1,
  normalizedCountry(item),
  item.countryCode.trim(),
  item.cityName,
  item.airportCode.trim(),
  item.airportName,
  nodeTypes[item.nodeType] ?? String(item.nodeType),
  item.loungeName,
  item.terminal || "—",
  item.floor || "—",
  flightTypes[item.flightType] ?? String(item.flightType),
  serviceTypes[item.serviceType] ?? item.serviceType,
  item.schedule || "Не указано",
  item.address || "Не указано",
  "Только 3",
  item.isClosed ? "Временно закрыт" : "Открыт",
  item.loungeId,
  loungeUrl(item),
  checkedAt,
]);
data.getRange(`A2:S${dataLastRow}`).values = rows;

data.getRange("A1:S1").format = {
  fill: "#0F6B45",
  font: { bold: true, color: "#FFFFFF" },
  horizontalAlignment: "center",
  verticalAlignment: "center",
  wrapText: true,
};
data.getRange("A1:S1").format.rowHeight = 32;
data.getRange(`A2:S${dataLastRow}`).format.verticalAlignment = "top";
for (const column of ["D", "F", "H", "M", "N", "R"]) {
  data.getRange(`${column}2:${column}${dataLastRow}`).format.wrapText = true;
}
data.getRange(`R2:R${dataLastRow}`).format.font = {
  color: "#176F48",
  underline: true,
};
data.getRange(`S2:S${dataLastRow}`).format.numberFormat = "yyyy-mm-dd";
data.getRange(`A2:A${dataLastRow}`).format.horizontalAlignment = "center";
data.getRange(`C2:C${dataLastRow}`).format.horizontalAlignment = "center";
data.getRange(`E2:G${dataLastRow}`).format.horizontalAlignment = "center";
data.getRange(`I2:M${dataLastRow}`).format.horizontalAlignment = "center";
data.getRange(`O2:Q${dataLastRow}`).format.horizontalAlignment = "center";
data.getRange(`S2:S${dataLastRow}`).format.horizontalAlignment = "center";
data.getRange(`A1:S${dataLastRow}`).format.borders = {
  insideHorizontal: { style: "thin", color: "#E0E8E3" },
  bottom: { style: "thin", color: "#C8D8CF" },
};

data.getRange(`P2:P${dataLastRow}`).conditionalFormats.add("containsText", {
  text: "Временно закрыт",
  format: {
    fill: "#FCE8E6",
    font: { bold: true, color: "#A33B32" },
  },
});
data.getRange(`P2:P${dataLastRow}`).conditionalFormats.add("containsText", {
  text: "Открыт",
  format: {
    fill: "#E7F4EC",
    font: { color: "#176F48" },
  },
});

const widths = {
  A: 6,
  B: 25,
  C: 12,
  D: 18,
  E: 10,
  F: 28,
  G: 13,
  H: 30,
  I: 12,
  J: 9,
  K: 17,
  L: 16,
  M: 18,
  N: 48,
  O: 13,
  P: 18,
  Q: 9,
  R: 40,
  S: 13,
};
for (const [column, width] of Object.entries(widths)) {
  data.getRange(`${column}1:${column}${dataLastRow}`).format.columnWidth = width;
}
data.freezePanes.freezeRows(1);
data.freezePanes.freezeColumns(2);

const table = data.tables.add(
  `A1:S${dataLastRow}`,
  true,
  "SberPremierForeignLounges",
);
table.style = "TableStyleMedium4";
table.showBandedRows = true;
table.showFilterButton = true;

const summaryCheck = await workbook.inspect({
  kind: "table",
  range: "Сводка!A1:H19",
  include: "values,formulas",
  tableMaxRows: 20,
  tableMaxCols: 8,
  maxChars: 7000,
});
console.log(summaryCheck.ndjson);
const dataCheck = await workbook.inspect({
  kind: "table",
  range: "Зарубежные залы!A1:S8",
  include: "values,formulas",
  tableMaxRows: 8,
  tableMaxCols: 19,
  maxChars: 9000,
});
console.log(dataCheck.ndjson);
const errors = await workbook.inspect({
  kind: "match",
  searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A",
  options: { useRegex: true, maxResults: 100 },
  summary: "final formula error scan",
});
console.log(errors.ndjson);

const summaryPreview = await workbook.render({
  sheetName: "Сводка",
  range: "A1:H19",
  scale: 1.5,
  format: "png",
});
await fs.writeFile(
  `${outputDir}/preview_summary.png`,
  new Uint8Array(await summaryPreview.arrayBuffer()),
);
const dataPreview = await workbook.render({
  sheetName: "Зарубежные залы",
  range: "A1:S15",
  scale: 1,
  format: "png",
});
await fs.writeFile(
  `${outputDir}/preview_data.png`,
  new Uint8Array(await dataPreview.arrayBuffer()),
);

await fs.mkdir(outputDir, { recursive: true });
const output = await SpreadsheetFile.exportXlsx(workbook);
await output.save(
  `${outputDir}/business_lounges_sberpremier_levels_2_3_foreign.xlsx`,
);
