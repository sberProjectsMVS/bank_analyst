import fs from "node:fs/promises";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const outputDir = "/Users/ilyashmarov/Documents/analyst/bank_analyst/outputs/pos_entry_thresholds_2026-08-05";
const outputPath = `${outputDir}/POS_границы_премиального_обслуживания.xlsx`;

const standalone = [
  ["Сбер", "СберПремьер — уровень 1", "Все регионы", 150000, "Не требуется", "POS — самостоятельная альтернатива", new Date("2026-08-04"), "https://premiumbanking.info/sber/1"],
  ["Сбер", "СберПремьер — уровень 2", "Все регионы", 200000, "Не требуется", "POS — самостоятельная альтернатива", new Date("2026-08-04"), "https://premiumbanking.info/sber/2"],
  ["Сбер", "СберПремьер — уровень 3", "Все регионы", 350000, "Не требуется", "POS — самостоятельная альтернатива", new Date("2026-08-04"), "https://premiumbanking.info/sber/3"],
  ["Газпромбанк", "Премиум — уровень 1", "Все регионы", 150000, "Не требуется", "POS — самостоятельная альтернатива", new Date("2026-07-21"), "https://www.gazprombank.ru/premium/gazprom-bonus/"],
  ["Райффайзен Банк", "Premium — по обороту покупок", "Все регионы", 150000, "Не требуется", "POS — самостоятельное условие", new Date("2026-08-04"), "https://premiumbanking.info/raiffeisen/2"],
];

const combined = [
  ["Т-Банк", "Premium Silver", "Все регионы", 200000, "AUM от 1 000 000 ₽", "AUM + POS", new Date("2026-07-21"), "https://www.tbank.ru/bank/help/general/premium/access/what-is/"],
  ["Альфа-Банк", "Alfa Only — уровень 2", "Все регионы", 200000, "AUM от 2 000 000 ₽", "AUM + POS", new Date("2026-08-04"), "https://premiumbanking.info/alfabank/2"],
  ["ВТБ", "Привилегия — Сапфир", "Москва и МО", 125000, "AUM от 1 500 000 ₽", "AUM + POS", new Date("2026-07-28"), "https://www.vtb.ru/promo/rsvtb-pv-2/"],
  ["ВТБ", "Привилегия — Сапфир", "Другие регионы", 100000, "AUM от 1 500 000 ₽", "AUM + POS", new Date("2026-07-28"), "https://www.vtb.ru/promo/rsvtb-pv-2/"],
  ["Газпромбанк", "Премиум — уровень 1", "Все регионы", 100000, "AUM от 1 000 000 ₽", "AUM + POS", new Date("2026-07-21"), "https://www.gazprombank.ru/premium/gazprom-bonus/"],
  ["Газпромбанк", "Премиум — уровень 1", "Все регионы", 50000, "Зарплата от 250 000 ₽", "Зарплата + POS", new Date("2026-07-21"), "https://www.gazprombank.ru/premium/gazprom-bonus/"],
  ["Газпромбанк", "Премиум — уровень 2", "Все регионы", 100000, "Зарплата от 750 000 ₽", "Зарплата + POS", new Date("2026-07-21"), "https://premiumbanking.info/gazprombank/2"],
  ["Инго Банк", "Инго Premium", "Все регионы", 75000, "AUM от 1 000 000 ₽", "AUM + POS", new Date("2026-07-28"), "https://cdn.ingos.ru/docs/cards/Tarif_7.pdf"],
  ["Инго Банк", "Инго Premium", "Все регионы", 75000, "Зачисления от 300 000 ₽", "Зачисления + POS", new Date("2026-07-28"), "https://cdn.ingos.ru/docs/cards/Tarif_7.pdf"],
];

const workbook = Workbook.create();
workbook.comments.setSelf({ displayName: "Ilyashmarov" });

function buildSheet(name, title, subtitle, rows, tableName) {
  const sheet = workbook.worksheets.add(name);
  sheet.showGridLines = false;
  sheet.freezePanes.freezeRows(6);

  sheet.getRange("A1:H1").merge();
  sheet.getRange("A1").values = [[title]];
  sheet.getRange("A1:H1").format = {
    fill: "#163A5F",
    font: { bold: true, color: "#FFFFFF", size: 16 },
    verticalAlignment: "center",
  };
  sheet.getRange("A1:H1").format.rowHeight = 30;

  sheet.getRange("A2:H2").merge();
  sheet.getRange("A2").values = [[subtitle]];
  sheet.getRange("A2:H2").format = {
    fill: "#EAF1F8",
    font: { color: "#26445F", italic: true, size: 10 },
    wrapText: true,
    verticalAlignment: "center",
  };
  sheet.getRange("A2:H2").format.rowHeight = 34;

  sheet.getRange("A4").values = [["Минимальный POS"]];
  sheet.getRange("B4").formulas = [[`=MIN(D7:D${6 + rows.length})`]];
  sheet.getRange("D4").values = [["Количество условий"]];
  sheet.getRange("E4").formulas = [[`=COUNTA(A7:A${6 + rows.length})`]];
  sheet.getRange("A4:E4").format = {
    fill: "#F3F6F9",
    font: { bold: true, color: "#163A5F" },
    borders: { preset: "outside", style: "thin", color: "#B8C6D1" },
  };
  sheet.getRange("B4").format.numberFormat = '#,##0" ₽"';
  sheet.getRange("E4").format.numberFormat = "#,##0";

  const headers = [["Банк", "Пакет / уровень", "Регион", "POS в месяц", "Дополнительное условие", "Логика входа", "Дата проверки", "Источник"]];
  sheet.getRange("A6:H6").values = headers;
  sheet.getRange(`A7:H${6 + rows.length}`).values = rows;
  const fullRange = sheet.getRange(`A6:H${6 + rows.length}`);
  const table = sheet.tables.add(`A6:H${6 + rows.length}`, true, tableName);
  table.style = "TableStyleMedium2";
  table.showFilterButton = true;

  sheet.getRange("A6:H6").format = {
    fill: "#2C628F",
    font: { bold: true, color: "#FFFFFF" },
    verticalAlignment: "center",
    wrapText: true,
  };
  sheet.getRange("A6:H6").format.rowHeight = 28;
  sheet.getRange(`D7:D${6 + rows.length}`).format.numberFormat = '#,##0" ₽"';
  sheet.getRange(`G7:G${6 + rows.length}`).format.numberFormat = "yyyy-mm-dd";
  sheet.getRange(`A7:C${6 + rows.length}`).format.verticalAlignment = "center";
  sheet.getRange(`D7:D${6 + rows.length}`).format.horizontalAlignment = "right";
  sheet.getRange(`E7:H${6 + rows.length}`).format = { wrapText: true, verticalAlignment: "center" };
  fullRange.format.borders = {
    insideHorizontal: { style: "thin", color: "#D6DEE5" },
    bottom: { style: "thin", color: "#A7B8C6" },
  };

  const widths = [18, 29, 18, 16, 25, 24, 15, 52];
  widths.forEach((width, index) => {
    sheet.getRangeByIndexes(0, index, 6 + rows.length, 1).format.columnWidth = width;
  });
  sheet.getRange(`A7:H${6 + rows.length}`).format.rowHeight = 34;

  rows.forEach((row, index) => {
    workbook.comments.addThread(
      { cell: sheet.getRange(`D${7 + index}`) },
      `Источник условия входа: ${row[7]}\nДата проверки: ${row[6].toISOString().slice(0, 10)}`,
    );
  });

  return sheet;
}

buildSheet(
  "POS — самостоятельно",
  "POS-пороги входа в премиальное обслуживание",
  "POS — ежемесячный оборот покупок по картам. В этой таблице POS является самостоятельным условием и не требует AUM, зарплаты или зачислений.",
  standalone,
  "StandalonePOSThresholds",
);

buildSheet(
  "POS + условие",
  "Комбинированные POS-пороги",
  "POS учитывается только вместе с дополнительным условием. AUM — общая сумма активов клиента в банке; POS — траты по картам за месяц.",
  combined,
  "CombinedPOSThresholds",
);

await fs.mkdir(outputDir, { recursive: true });

const standaloneCheck = await workbook.inspect({
  kind: "table",
  range: "'POS — самостоятельно'!A1:H11",
  include: "values,formulas",
  tableMaxRows: 14,
  tableMaxCols: 8,
});
console.log(standaloneCheck.ndjson);

const combinedCheck = await workbook.inspect({
  kind: "table",
  range: "'POS + условие'!A1:H15",
  include: "values,formulas",
  tableMaxRows: 18,
  tableMaxCols: 8,
});
console.log(combinedCheck.ndjson);

const errorCheck = await workbook.inspect({
  kind: "match",
  searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A",
  options: { useRegex: true, maxResults: 100 },
  summary: "final formula error scan",
});
console.log(errorCheck.ndjson);

for (const sheetName of ["POS — самостоятельно", "POS + условие"]) {
  const preview = await workbook.render({
    sheetName,
    autoCrop: "all",
    scale: 1.5,
    format: "png",
  });
  const safeName = sheetName === "POS — самостоятельно" ? "standalone" : "combined";
  await fs.writeFile(`${outputDir}/preview_${safeName}.png`, new Uint8Array(await preview.arrayBuffer()));
}

const output = await SpreadsheetFile.exportXlsx(workbook);
await output.save(outputPath);
console.log(outputPath);
