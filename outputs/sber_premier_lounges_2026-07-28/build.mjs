import fs from "node:fs/promises";
import https from "node:https";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const outputDir =
  "/Users/ilyashmarov/Documents/analyst/bank_analyst/outputs/sber_premier_lounges_2026-07-28";
const apiBase = "https://mir.pass.nspk.ru/sber-pass/api/v1/typeReference";
const checkedAt = new Date(2026, 6, 28);
const checkedAtText = "2026-07-28";

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
              new Error(`HTTP ${response.statusCode} for ${url}: ${body.slice(0, 300)}`),
            );
            return;
          }
          try {
            resolve(JSON.parse(body));
          } catch (error) {
            reject(error);
          }
        });
      },
    );
    request.on("error", reject);
  });
}

function loungeUrl(item, packageId) {
  const params = new URLSearchParams({
    airportCode: item.airportCode,
    loungeId: String(item.loungeId),
    package: packageId,
  });
  return `https://mir.pass.nspk.ru/sber/ru/lounges?${params.toString()}`;
}

const dateTime = "2026-07-28T12:00";
const commonParams = new URLSearchParams({
  locale: "ru",
  countryCode: "RUS",
  dateTime,
});
const level2Params = new URLSearchParams(commonParams);
level2Params.set("productId", "programm6");
const level3Params = new URLSearchParams(commonParams);
level3Params.set("productId", "programm7");

const [level2, level3, hashInfo] = await Promise.all([
  fetchJson(`${apiBase}/loungeList?${level2Params.toString()}`),
  fetchJson(`${apiBase}/loungeList?${level3Params.toString()}`),
  fetchJson(`${apiBase}/loungeHash?locale=ru`),
]);

const level2Ids = new Set(level2.map((item) => item.loungeId));
const level3Ids = new Set(level3.map((item) => item.loungeId));
const unionIds = new Set([...level2Ids, ...level3Ids]);
if (
  level2Ids.size !== level3Ids.size ||
  [...level2Ids].some((id) => !level3Ids.has(id))
) {
  throw new Error("Российские перечни уровней 2 и 3 не совпадают");
}

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

const lounges = [...level2].sort((left, right) =>
  [
    left.cityName.localeCompare(right.cityName, "ru"),
    left.airportName.localeCompare(right.airportName, "ru"),
    left.loungeName.localeCompare(right.loungeName, "ru"),
  ].find((value) => value !== 0) ?? 0,
);

const workbook = Workbook.create();
const summary = workbook.worksheets.add("Сводка");
const data = workbook.worksheets.add("Залы");
summary.showGridLines = false;
data.showGridLines = false;

summary.getRange("A1:H1").merge();
summary.getRange("A1").values = [["Бизнес-залы СберПремьер в России"]];
summary.getRange("A2:H2").merge();
summary.getRange("A2").values = [
  [
    "Официальный перечень для 2-го и 3-го уровней. Срез на 28 июля 2026 года.",
  ],
];

summary.getRange("A4:A8").values = [
  ["В каталоге"],
  ["Открыты"],
  ["Временно закрыты"],
  ["Городов"],
  ["Транспортных узлов"],
];
summary.getRange("B4").formulas = [["=COUNTA('Залы'!A2:A104)"]];
summary.getRange("B5").formulas = [
  ["=COUNTIF('Залы'!N2:N104,\"Открыт\")"],
];
summary.getRange("B6").formulas = [
  ["=COUNTIF('Залы'!N2:N104,\"Временно закрыт\")"],
];
summary.getRange("B7:B8").values = [
  [new Set(lounges.map((item) => item.cityName)).size],
  [new Set(lounges.map((item) => item.airportCode)).size],
];

summary.getRange("D4:E8").values = [
  ["Уровень 2", "Уровень 3"],
  ["Россия", "Россия и зарубежье"],
  ["Российских залов", unionIds.size],
  ["Состав в России", "Совпадает"],
  ["Проверено", checkedAt],
];
summary.getRange("D6").values = [["Российских залов"]];
summary.getRange("E6").formulas = [["='Сводка'!B4"]];
summary.getRange("E8").format.numberFormat = "yyyy-mm-dd";

summary.getRange("A10:H10").merge();
summary.getRange("A10").values = [["Что важно"]];
summary.getRange("A11:H11").merge();
summary.getRange("A11").values = [
  [
    "Для российских залов официальный каталог возвращает один и тот же перечень для СберПремьер 2-го и 3-го уровней. Различаются количество проходов и зарубежная география 3-го уровня.",
  ],
];
summary.getRange("A12:H12").merge();
summary.getRange("A12").values = [
  [
    "В каталоге 103 позиции: 101 открыта, 2 помечены оператором как временно закрытые. Закрытые позиции сохранены в таблице и выделены цветом.",
  ],
];
summary.getRange("A13:H13").merge();
summary.getRange("A13").values = [
  [
    `Каталог оператора обновлён ${String(hashInfo.updateDate).slice(0, 10)}; проверка выполнена ${checkedAtText}. Состав может меняться без предварительного уведомления.`,
  ],
];
summary.getRange("A15:H15").merge();
summary.getRange("A15").values = [["Официальные источники"]];
summary.getRange("A16:H16").merge();
summary.getRange("A16").values = [
  ["https://mir.pass.nspk.ru/sber/ru"],
];
summary.getRange("A17:H17").merge();
summary.getRange("A17").values = [
  [`${apiBase}/loungeList?${level2Params.toString()}`],
];

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
summary.getRange("A4:A8").format = {
  fill: "#F3F6F4",
  font: { bold: true, color: "#52645A" },
};
summary.getRange("B4:B8").format = {
  fill: "#FFFFFF",
  font: { bold: true, color: "#16251D", size: 16 },
  horizontalAlignment: "center",
};
summary.getRange("A4:B8").format.borders = {
  preset: "outside",
  style: "thin",
  color: "#C8D8CF",
};
summary.getRange("D4:E8").format.borders = {
  preset: "outside",
  style: "thin",
  color: "#C8D8CF",
};
summary.getRange("D4:E4").format = {
  fill: "#0F6B45",
  font: { bold: true, color: "#FFFFFF" },
  horizontalAlignment: "center",
};
summary.getRange("D5:D8").format = {
  fill: "#F3F6F4",
  font: { bold: true, color: "#52645A" },
};
summary.getRange("E5:E8").format = {
  fill: "#FFFFFF",
  horizontalAlignment: "center",
};
summary.getRange("A10:H10").format = {
  fill: "#DDEEE5",
  font: { bold: true, color: "#0F6B45", size: 13 },
};
summary.getRange("A11:H13").format = {
  fill: "#F8FBF9",
  font: { color: "#27382F" },
  wrapText: true,
  verticalAlignment: "center",
};
summary.getRange("A11:H13").format.rowHeight = 34;
summary.getRange("A15:H15").format = {
  fill: "#DDEEE5",
  font: { bold: true, color: "#0F6B45", size: 13 },
};
summary.getRange("A16:H17").format = {
  font: { color: "#176F48", underline: true },
  wrapText: true,
};
summary.getRange("A1:H17").format.columnWidth = 13;
summary.getRange("A1:A17").format.columnWidth = 21;
summary.getRange("B1:B17").format.columnWidth = 14;
summary.getRange("C1:C17").format.columnWidth = 3;
summary.getRange("D1:D17").format.columnWidth = 21;
summary.getRange("E1:E17").format.columnWidth = 20;

const headers = [
  "№",
  "Город",
  "Код",
  "Транспортный узел",
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
data.getRange("A1:Q1").values = [headers];
const rows = lounges.map((item, index) => [
  index + 1,
  item.cityName,
  item.airportCode,
  item.airportName,
  nodeTypes[item.nodeType] ?? String(item.nodeType),
  item.loungeName,
  item.terminal || "—",
  item.floor || "—",
  flightTypes[item.flightType] ?? String(item.flightType),
  serviceTypes[item.serviceType] ?? item.serviceType,
  item.schedule || "Не указано",
  item.address || "Не указано",
  "2 и 3",
  item.isClosed ? "Временно закрыт" : "Открыт",
  item.loungeId,
  loungeUrl(item, "programm6"),
  checkedAt,
]);
data.getRange(`A2:Q${rows.length + 1}`).values = rows;

data.getRange("A1:Q1").format = {
  fill: "#0F6B45",
  font: { bold: true, color: "#FFFFFF" },
  horizontalAlignment: "center",
  verticalAlignment: "center",
  wrapText: true,
};
data.getRange("A1:Q1").format.rowHeight = 32;
data.getRange(`A2:Q${rows.length + 1}`).format = {
  verticalAlignment: "top",
};
data.getRange(`F2:F${rows.length + 1}`).format.wrapText = true;
data.getRange(`D2:D${rows.length + 1}`).format.wrapText = true;
data.getRange(`K2:K${rows.length + 1}`).format.wrapText = true;
data.getRange(`L2:L${rows.length + 1}`).format.wrapText = true;
data.getRange(`P2:P${rows.length + 1}`).format = {
  font: { color: "#176F48", underline: true },
  wrapText: true,
};
data.getRange(`Q2:Q${rows.length + 1}`).format.numberFormat = "yyyy-mm-dd";
data.getRange(`A2:A${rows.length + 1}`).format.horizontalAlignment = "center";
data.getRange(`C2:C${rows.length + 1}`).format.horizontalAlignment = "center";
data.getRange(`G2:J${rows.length + 1}`).format.horizontalAlignment = "center";
data.getRange(`M2:O${rows.length + 1}`).format.horizontalAlignment = "center";
data.getRange(`Q2:Q${rows.length + 1}`).format.horizontalAlignment = "center";
data.getRange(`A1:Q${rows.length + 1}`).format.borders = {
  insideHorizontal: { style: "thin", color: "#E0E8E3" },
  bottom: { style: "thin", color: "#C8D8CF" },
};

data.getRange(`N2:N${rows.length + 1}`).conditionalFormats.add(
  "containsText",
  {
    text: "Временно закрыт",
    format: {
      fill: "#FCE8E6",
      font: { bold: true, color: "#A33B32" },
    },
  },
);
data.getRange(`N2:N${rows.length + 1}`).conditionalFormats.add(
  "containsText",
  {
    text: "Открыт",
    format: {
      fill: "#E7F4EC",
      font: { color: "#176F48" },
    },
  },
);

data.getRange(`A1:A${rows.length + 1}`).format.columnWidth = 6;
data.getRange(`B1:B${rows.length + 1}`).format.columnWidth = 18;
data.getRange(`C1:C${rows.length + 1}`).format.columnWidth = 9;
data.getRange(`D1:D${rows.length + 1}`).format.columnWidth = 25;
data.getRange(`E1:E${rows.length + 1}`).format.columnWidth = 14;
data.getRange(`F1:F${rows.length + 1}`).format.columnWidth = 28;
data.getRange(`G1:H${rows.length + 1}`).format.columnWidth = 11;
data.getRange(`I1:I${rows.length + 1}`).format.columnWidth = 17;
data.getRange(`J1:J${rows.length + 1}`).format.columnWidth = 18;
data.getRange(`K1:K${rows.length + 1}`).format.columnWidth = 18;
data.getRange(`L1:L${rows.length + 1}`).format.columnWidth = 48;
data.getRange(`M1:N${rows.length + 1}`).format.columnWidth = 18;
data.getRange(`O1:O${rows.length + 1}`).format.columnWidth = 9;
data.getRange(`P1:P${rows.length + 1}`).format.columnWidth = 40;
data.getRange(`Q1:Q${rows.length + 1}`).format.columnWidth = 13;
data.freezePanes.freezeRows(1);
data.freezePanes.freezeColumns(2);

const table = data.tables.add(`A1:Q${rows.length + 1}`, true, "SberPremierLounges");
table.style = "TableStyleMedium4";
table.showBandedRows = true;
table.showFilterButton = true;

const summaryCheck = await workbook.inspect({
  kind: "table",
  range: "Сводка!A1:H17",
  include: "values,formulas",
  tableMaxRows: 20,
  tableMaxCols: 8,
  maxChars: 6000,
});
console.log(summaryCheck.ndjson);
const dataCheck = await workbook.inspect({
  kind: "table",
  range: "Залы!A1:Q8",
  include: "values,formulas",
  tableMaxRows: 8,
  tableMaxCols: 17,
  maxChars: 7000,
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
  range: "A1:H17",
  scale: 1.5,
  format: "png",
});
await fs.writeFile(
  `${outputDir}/preview_summary.png`,
  new Uint8Array(await summaryPreview.arrayBuffer()),
);
const dataPreview = await workbook.render({
  sheetName: "Залы",
  range: "A1:Q16",
  scale: 1,
  format: "png",
});
await fs.writeFile(
  `${outputDir}/preview_data.png`,
  new Uint8Array(await dataPreview.arrayBuffer()),
);

await fs.mkdir(outputDir, { recursive: true });
const output = await SpreadsheetFile.exportXlsx(workbook);
await output.save(`${outputDir}/business_lounges_sberpremier_levels_2_3_russia.xlsx`);
