// ═══════════════════════════════════════════════════════════════════════════
//  LUNA · БИБЛИЯ СЕТОВ v4 · Google Sheets Macro
//  Extensions -> Apps Script -> buildBibliyaSetov()
// ═══════════════════════════════════════════════════════════════════════════

function buildBibliyaSetov() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const sheets = ["RUN SHEET", "SCRIPТЫ RU", "SCRIPTS EN", "RUN SHEET EN", "SALES RU", "SALES EN", "SALES PRINT"];
  sheets.forEach(n => { const s = ss.getSheetByName(n); if (s) ss.deleteSheet(s); });
  buildRunSheet(ss);
  buildScriptsRU(ss);
  buildScriptsEN(ss);
  buildRunSheetEN(ss);
  buildSalesRU(ss);
  buildSalesEN(ss);
  buildSalesPrint(ss);
  ss.setActiveSheet(ss.getSheetByName("RUN SHEET"));
  SpreadsheetApp.getUi().alert("OK LUNA Библия Сетов v4 - 7 листов созданы!");
}

// ─────────────────────────────────────────────────────────────────────────
//  HELPERS
// ─────────────────────────────────────────────────────────────────────────
const P = {
  BK:"0D0D0D", GD:"D4A853", GL:"F5E6C8", CR:"FDF6EE", C2:"F5ECD8",
  WH:"FFFFFF", RD:"8B1A1A", GR:"2C4A2E", NV:"1E3A5F",
  DK:"1A1A1A", MD:"3A3A3A", BR:"B8922E",
  GONG:"4A0E0E", GONG_L:"FFF5F0",
  FIN:"0E2A1A", FIN_L:"E8F5EE",
  CHEF:"1A2A4A", CHEF_L:"D6E4F0", CHEF_BDR:"6A9FC0",
  WAITER:"3A2000", WAITER_L:"FFF8EE",
  PUR:"3C3489", PUR_L:"EEEDFE",
  GRN:"27500A", GRN_L:"EAF3DE",
  AMB:"633806", AMB_L:"FAEEDA",
};

function S(range, opts) {
  if (opts.bg)        range.setBackground("#"+opts.bg);
  if (opts.fontColor) range.setFontColor("#"+opts.fontColor);
  if (opts.bold)      range.setFontWeight("bold");
  if (opts.italic)    range.setFontStyle("italic");
  if (opts.size)      range.setFontSize(opts.size);
  if (opts.hAlign)    range.setHorizontalAlignment(opts.hAlign);
  if (opts.vAlign)    range.setVerticalAlignment(opts.vAlign);
  if (opts.wrap)      range.setWrapStrategy(SpreadsheetApp.WrapStrategy.WRAP);
  range.setFontFamily("Montserrat");
}
function B(range, color, thick) {
  range.setBorder(true,true,true,true,false,false,"#"+color,
    thick ? SpreadsheetApp.BorderStyle.SOLID_MEDIUM : SpreadsheetApp.BorderStyle.SOLID);
}
function titleBlock(ws, cols, title, sub) {
  const last = String.fromCharCode(64+cols);
  ws.setRowHeight(1,52);
  const r1=ws.getRange("A1:"+last+"1"); ws.getRange("A1").setValue(title);
  r1.merge(); S(r1,{bg:P.BK,fontColor:P.GD,bold:true,size:22,hAlign:"center",vAlign:"middle"});
  ws.setRowHeight(2,22);
  const r2=ws.getRange("A2:"+last+"2"); ws.getRange("A2").setValue(sub);
  r2.merge(); S(r2,{bg:P.BK,fontColor:P.GL,italic:true,size:9,hAlign:"center",vAlign:"middle"});
  ws.setRowHeight(3,5);
  ws.getRange("A3:"+last+"3").merge().setBackground("#"+P.GD);
}

// ─────────────────────────────────────────────────────────────────────────
//  SHEET 1 · RUN SHEET (RU)
// ─────────────────────────────────────────────────────────────────────────
function buildRunSheet(ss) {
  const ws = ss.insertSheet("RUN SHEET");
  [200,80,100,320,90,200,110,115,90,80,60,260].forEach((w,i)=>ws.setColumnWidth(i+1,w));
  titleBlock(ws,12,"LUNA - GASTRO THEATER","БИБЛИЯ СЕТОВ v4  |  SERVICE RUN SHEET  |  до 10 гостей  |  MICHELIN FINE DINING");

  ws.setRowHeight(4,22);
  [["A4","Дата:"],["B4","_______________"],["D4","Стол:"],["E4","___"],
   ["G4","Гостей:"],["H4","___"],["J4","Официант:"],["K4","_______________"]].forEach(([c,v])=>{
    const r=ws.getRange(c); r.setValue(v); S(r,{fontColor:P.MD,bold:true,size:9,hAlign:"left",vAlign:"middle"});
  });
  ws.setRowHeight(5,5); ws.getRange("A5:L5").merge().setBackground("#"+P.GD);

  ws.setRowHeight(6,40);
  ["ЭТАП","TIME","КТО","ДЕЙСТВИЕ / ТЕКСТ","БЛЮДО\nВЫНОС","ШОУ-\nЭЛЕМЕНТ",
   "ВИНО\nНАЛИВ","FEEDBACK\nГОСТЯ","КЛИР","TIME\nEND","MIN","ЗАМЕТКИ"].forEach((h,i)=>{
    const r=ws.getRange(6,i+1); r.setValue(h);
    S(r,{bg:P.BK,fontColor:P.WH,bold:true,size:9,hAlign:"center",vAlign:"middle",wrap:true}); B(r,P.BR);
  });

  const rows = [
    {t:"CHEF", d:["РЕЧЬ ШЕФА\nОТКРЫТИЕ","18:50","Шеф",
      "18:50 - Шеф выходит к столу. Приветствует гостей лично. Рассказывает историю LUNA, концепцию сета, свой путь. Тон: личный, медленный, без спешки. ~10 минут.",
      "","","","","","19:00","10","(!) Официант стоит рядом, не вмешивается. Музыка фоном - не выключать."]},
    {t:"WAITER_BRIDGE", d:["СВЯЗКА\nОФИЦИАНТА","19:00","Официант",
      "19:00 - Официант делает шаг вперёд. Коротко завершает вступление (30–45 сек): называет себя, объявляет начало сета, подводит к гонгу.",
      "","","","","","19:01","1","Финальная фраза перед гонгом: «Позвольте открыть вечер.»"]},
    {t:"GONG_OPEN", d:["ГОНГ x1\nСТАРТ СЕТА","19:01","Официант",
      "19:01 - Один чёткий удар. 3–4 секунды полной тишины. Официант возвращает взгляд к гостям.",
      "","ГОНГ x1\nСТАРТ","","","","19:02","1","(!) Тишина после удара обязательна. Не торопить."]},
    {t:"COURSE", d:["COURSE 1\nYuzu Oyster","19:02","Официант",
      "19:02 - Устрица, кимчи-томато, юзу. Акцент: текстура, свежесть, первое впечатление.",
      "19:02","Подача на льду\n+ дымовой элемент","19:03\nCava pour","19:05","19:09","19:10","8","Cava: Grifol Brut"]},
    {t:"COURSE", d:["COURSE 2\nTotoro Tuna\n«Purple Cloud»","19:12","Официант",
      "19:13 - Тунец + икра, пурпурное облако, минеральная структура вина.",
      "19:14","«Облако»\ndry ice","19:14\nWine pour","19:17","19:20","19:21","9","Wine: Le Vent Dans Les Voiles"]},
    {t:"TOWEL", d:[
      "ПОЛОТЕНЦЕ\nДЛЯ РУК","19:21","Официант",
      "19:21 - Официант выносит холодное ароматное полотенце для рук каждому гостю. Блюда 2, 4, 6 едят руками - полотенце подаётся сразу после того, как все гости закончили.",
      "","","","","","","","(!!) Обязательно. Подаётся аккуратно, без спешки. По одному каждому гостю."]},
    {t:"COURSE", d:["COURSE 3\nBread & Liver","19:23","Официант",
      "19:24 - Переосмысление классики, малина + кокос. Намеренная пауза без вина - объяснить до выноса.",
      "19:25","переходный\nмомент","NO WINE","19:27","19:30","19:31","8","Пауза вина - объяснить до выноса"]},
    {t:"COURSE", d:["COURSE 4\nCrab Omelette 2.0\n«Jay Fai Tribute»","19:33","Официант",
      "19:34 - Огонь, скорость, контроль. Краб + икра. Шардоне - кремовость, сладость краба.",
      "19:35","","19:35\nChardonnay","19:38","19:41","19:42","9","Wine: Little Things Chardonnay"]},
    {t:"TOWEL", d:[
      "ПОЛОТЕНЦЕ\nДЛЯ РУК","19:42","Официант",
      "19:42 - Официант выносит холодное ароматное полотенце для рук каждому гостю. Блюда 2, 4, 6 едят руками - полотенце подаётся сразу после того, как все гости закончили.",
      "","","","","","","","(!!) Обязательно. Подаётся аккуратно, без спешки. По одному каждому гостю."]},
    {t:"COURSE", d:["COURSE 5\nThai Ceviche\n(Red Snapper)","19:44","Официант",
      "19:45 - Движение, свежесть. Без вина - чистота вкуса. Снаппер с рифов Самуи.",
      "19:46","","NO WINE","19:48","19:51","19:52","8","Без вина - объяснить гостю"]},
    {t:"COURSE", d:["COURSE 6\nWagyu Tartare","19:54","Официант",
      "19:55 - Тихая роскошь. Вагю в чистом виде. Пино - элегантность, баланс, не перебивает.",
      "19:56","","19:56\nPinot Noir","19:59","20:03","20:04","10","Wine: Pinot Noir D'Doumah"]},
    {t:"TOWEL", d:[
      "ПОЛОТЕНЦЕ\nДЛЯ РУК","20:04","Официант",
      "20:04 - Официант выносит холодное ароматное полотенце для рук каждому гостю. Блюда 2, 4, 6 едят руками - полотенце подаётся сразу после того, как все гости закончили.",
      "","","","","","","","(!!) Обязательно. Подаётся аккуратно, без спешки. По одному каждому гостю."]},
    {t:"COURSE", d:["COURSE 7\nLobster Ravioli","20:06","Официант",
      "20:07 - Контраст: сладость лобстера против глубины рокфора. Шардоне - мост между ними.",
      "20:08","Финиш соусом\nу стола","20:08\nChardonnay","20:11","20:15","20:16","10","Wine: Adelaide Hills Chardonnay"]},
    {t:"COURSE", d:["COURSE 8\nChocolate &\nRaspberry","20:18","Официант",
      "20:19 - Шоколад + кислота малины + тепло тонки. Малый ресет перед кульминацией.",
      "20:20","","NO WINE","20:22","20:24","20:25","7","Без вина - объяснить гостю"]},
    {t:"MAIN", d:["COURSE 9\nWagyu Truffle\n* MAIN","20:27","Официант",
      "20:28 - Кульминация. Вагю + трюфель. Кьянти - структура и пряность. Замедлить темп.",
      "20:29","Трюфель\nнатирается у стола","20:29\nChianti","20:33","20:38","20:39","12","Wine: Fattoria Villa Saletta Chianti"]},
    {t:"COURSE", d:["COURSE 10\nHoney Pear\n«Finale»","20:41","Официант",
      "20:42 - Груша + ваниль + трюфельная глубина. Мускат - флоральность и долгое послевкусие.",
      "20:43","Финальная свеча\nу стола","20:43\nMuscat","20:46","20:52","20:53","12","Wine: Muscat Beaumes de Venise"]},
    {t:"GONG_CLOSE", d:["ГОНГ x2\nЗАВЕРШЕНИЕ","20:55","Официант\n+ Управляющий",
      "20:55 - Выходят вместе. Первый удар - пауза 2–3 сек - второй удар. Тишина. Управляющий делает шаг вперёд.",
      "","ГОНГ x2\nФИНАЛ","","","","20:56","1","(!) После второго удара - полная тишина."]},
    {t:"CLOSING", d:["ФИНАЛ\nУПРАВЛЯЮЩЕГО","20:56","Управляющий",
      "20:56 - Финальное слово (~2–3 мин). Благодарит гостей. Вручает мерч LUNA каждому лично.",
      "","Мерч LUNA\nличное вручение","","","","21:00","4","При 2–4 гостях ~1 мин. При 10 ~2,5 мин."]},
  ];

  let ci2 = 0;
  rows.forEach((row,ri) => {
    const sr=ri+7;
    const hMap={CHEF:80,WAITER_BRIDGE:50,GONG_OPEN:48,COURSE:60,MAIN:64,GONG_CLOSE:50,CLOSING:72,TOWEL:44};
    ws.setRowHeight(sr, hMap[row.t]||60);
    const even = ci2%2===0;
    if (row.t==="COURSE"||row.t==="MAIN") ci2++;
    const {t,d}=row;
    d.forEach((val,ci) => {
      const cell=ws.getRange(sr,ci+1);
      cell.setValue(val); S(cell,{vAlign:"middle",wrap:true});
      const noW=String(val).includes("NO WINE");
      if (t==="CHEF") {
        const bgs=[P.CHEF_L,P.CHEF_L,"D6E4F0","EAF2FC",P.BK,P.BK,P.BK,P.BK,P.BK,P.CHEF_L,P.CHEF_L,"EAF2FC"];
        const fcs=[P.CHEF,P.CHEF,P.CHEF,P.CHEF,P.BK,P.BK,P.BK,P.BK,P.BK,P.CHEF,P.CHEF,P.CHEF];
        S(cell,{bg:bgs[ci]||P.CR,fontColor:fcs[ci]||P.MD,size:9,bold:ci<=1||ci===10,italic:ci===2,hAlign:ci===3||ci===11?"left":"center"});
        B(cell,P.CHEF_BDR,ci===0);
      } else if (t==="WAITER_BRIDGE") {
        S(cell,{bg:ci===3||ci===11?P.WAITER_L:"FFF8F0",fontColor:P.WAITER,size:9,bold:ci<=1||ci===10,italic:ci===2,hAlign:ci===3||ci===11?"left":"center"});
        B(cell,"C8940A",ci===0);
      } else if (t==="GONG_OPEN") {
        S(cell,{bg:ci===5?P.GONG_L:P.GONG_L,fontColor:ci===5||ci===0||ci===1||ci===10?P.GONG:P.MD,bold:ci<=1||ci===5||ci===10,size:9,hAlign:ci===3||ci===11?"left":"center"});
        B(cell,P.GONG,ci===0||ci===5);
      } else if (t==="GONG_CLOSE") {
        S(cell,{bg:"F0FDF4",fontColor:ci===5||ci===0||ci===1||ci===10?P.FIN:P.MD,bold:ci<=1||ci===5||ci===10,size:9,hAlign:ci===3||ci===11?"left":"center"});
        B(cell,"2C7A4E",ci===0||ci===5);
      } else if (t==="CLOSING") {
        S(cell,{bg:ci===5?"E8F5EE":"F0FDF4",fontColor:ci===5||ci===0||ci===1||ci===10?P.FIN:P.MD,bold:ci<=1||ci===5||ci===10,italic:ci===2,size:9,hAlign:ci===3||ci===11?"left":"center"});
        B(cell,"2C7A4E",ci===0);
      } else if (t==="MAIN") {
        const bgs9=[P.GL,"FEF8F0","FFF5F0",P.CR,"F5FFFC","F0F4FF","FFFFF8",P.CR,P.CR,P.GL,P.BK,P.CR];
        const fcs9=["9A7420",P.RD,P.RD,P.DK,P.GR,P.NV,"9A7420",P.MD,P.MD,"9A7420",P.GD,P.MD];
        S(cell,{bg:bgs9[ci]||P.CR,fontColor:fcs9[ci]||P.MD,bold:ci<=1||ci===4||ci===10,italic:ci===2||ci===5,size:ci===10?11:9,hAlign:ci===3||ci===11?"left":"center"});
        B(cell,P.BR,ci===0);
      } else {
        const bg=even?P.CR:P.C2;
        if (ci===0)      {S(cell,{bg:"F0E8D0",fontColor:P.BK,bold:true,size:9,hAlign:"center"});B(cell,P.BR,true);}
        else if (ci===1) {S(cell,{bg,fontColor:P.RD,bold:true,size:10,hAlign:"center"});B(cell,P.BR);}
        else if (ci===2) {S(cell,{bg:"FFF8EE",fontColor:P.WAITER,italic:true,size:8,hAlign:"center"});B(cell,P.BR);}
        else if (ci===3) {S(cell,{bg,fontColor:P.DK,size:8,hAlign:"left"});B(cell,P.BR);}
        else if (ci===4) {S(cell,{bg,fontColor:P.GR,bold:true,size:9,hAlign:"center"});B(cell,P.BR);}
        else if (ci===5) {S(cell,{bg:"F0F4FF",fontColor:P.NV,italic:true,size:8,hAlign:"left"});B(cell,P.BR);}
        else if (ci===6) {S(cell,{bg:"FFFFF8",fontColor:noW?"999999":P.BR,italic:noW,size:8,hAlign:"center"});B(cell,P.BR);}
        else if (ci===10){S(cell,{bg:P.BK,fontColor:P.GD,bold:true,size:10,hAlign:"center"});B(cell,P.BR);}
        else if (ci===11){S(cell,{bg,fontColor:P.MD,italic:true,size:8,hAlign:"left"});B(cell,P.BR);}
        else             {S(cell,{bg,fontColor:P.MD,size:8,hAlign:"center"});B(cell,P.BR);}
      }
    });
  });

  const tr=rows.length+7; ws.setRowHeight(tr,28);
  const tl=ws.getRange(tr,1,1,10); tl.merge();
  ws.getRange(tr,1).setValue("TOTAL  -  от выхода шефа до вручения мерча LUNA");
  S(tl,{bg:P.BK,fontColor:P.WH,bold:true,size:9,hAlign:"center",vAlign:"middle"}); B(tl,P.GD,true);
  const td=ws.getRange(tr,11); td.setValue("~130 мин");
  S(td,{bg:P.BK,fontColor:P.GD,bold:true,size:10,hAlign:"center",vAlign:"middle"}); B(td,P.GD,true);
  const tt=ws.getRange(tr,12); tt.setValue("18:50 -> 21:00");
  S(tt,{bg:P.BK,fontColor:P.GL,size:9,hAlign:"center",vAlign:"middle"}); B(tt,P.GD,true);
  ws.setFrozenRows(6);
}

// ─────────────────────────────────────────────────────────────────────────
//  SHARED: scripts data
// ─────────────────────────────────────────────────────────────────────────
function getScriptsData() {
  return [
    {t:"CHEF", h:220, label:"РЕЧЬ ШЕФА\nОТКРЫТИЕ\n18:50\n~10 минут",
     ru:"Добрый вечер.\n\nЯ рад, что вы здесь.\n\nМеня зовут [имя шефа]. Я готовлю в LUNA.\n\nПрежде чем мы начнём - я хочу рассказать вам кое-что. Не о меню. О том, как это всё появилось.\n\n[Личная история шефа - путь, вдохновение, почему Самуи, почему этот формат.]\n\nКаждое блюдо сегодня - это разговор. Между кухней и столом, между Азией и Европой, между тем, что я помню, и тем, что хочу показать вам.\n\nСет состоит из десяти курсов. У каждого - своя история. Мой официант [имя] расскажет её вам.\n\nСпасибо, что пришли.",
     en:"Good evening.\n\nI'm glad you're here.\n\nMy name is [chef's name]. I cook at LUNA.\n\nBefore we begin - I want to tell you something. Not about the menu. About how all of this came to be.\n\n[Chef's personal story - the journey, inspiration, why Samui, why this format.]\n\nEvery dish tonight is a conversation. Between the kitchen and the table, between Asia and Europe, between what I remember and what I want to show you.\n\nThe set consists of ten courses. Each one has its own story. My waiter [name] will tell it to you.\n\nThank you for being here."},
    {t:"WAITER", h:80, label:"СВЯЗКА\nОФИЦИАНТА\n19:00\n~45 сек",
     ru:"Меня зовут [имя]. Я ваш официант сегодня вечером.\n\nКаждый курс я буду представлять лично - коротко, но по существу.\n\nПозвольте открыть вечер.",
     en:"My name is [name]. I'll be your waiter this evening.\n\nI'll introduce each course personally - briefly, but with intention.\n\nAllow me to open the evening."},
    {t:"GONG", h:80, label:"ГОНГ x1\nСТАРТ\n19:01",
     ru:"[Официант берёт гонг. Пауза. Взгляд на гостей.]\n\n[Один чёткий удар.]\n\n[3–4 секунды полной тишины.]\n\n[Официант опускает гонг. Первый курс выносится.]",
     en:"[Waiter takes the gong. Pause. Makes eye contact with guests.]\n\n[One clean, deliberate strike.]\n\n[3–4 seconds of complete silence.]\n\n[Waiter sets down the gong. First course is served.]"},
    ["Course 1 - Yuzu Oyster","Мы начинаем с океана. Устрица формируется движением волны - поэтому текстура такая живая и деликатная. Мы добавляем кимчи-томато для мягкой ферментированной глубины, и юзу - чтобы поднять натуральную сладость. Кава здесь как рамка - её кислотность и пузырьки заостряют свежесть и готовят ваше нёбо к первому впечатлению.",
     "We begin with the ocean. The oyster is shaped by the movement of the water - that's why the texture feels so alive and delicate. We add kimchi tomato for gentle fermented depth, and yuzu to lift its natural sweetness. The cava works here almost like a frame - its acidity and bubbles sharpen the freshness and prepare your palate for the very first impression."],
    ["Course 2 - Totoro Tuna «Purple Cloud»","Этот курс вдохновлён визуальным хаосом азиатских городов - переплетёнными проводами над улицей. Пурпурное облако даёт неожиданную текстуру. Тунец и икра - точность и чистота. Вино очень минеральное, линейное - оно следует структуре блюда, не перебивая, а фокусируя.",
     "This course is inspired by the visual chaos of Asian cities - the tangled wires above the streets. The purple cloud gives an almost unexpected texture. Tuna and caviar bring precision and purity. The wine is very mineral and linear - it follows the structure of the dish, keeping everything clean and focused."],
    ["Course 3 - Bread & Liver (No Wine)","Сейчас мы делаем намеренную паузу - без вина. Это переосмысление очень классического: паштет и хлеб. Но с яркостью малины и текстурой кокоса. Это момент перехода - позвольте ему просто случиться.",
     "Here we pause intentionally - no wine. This is a reinterpretation of something very classic: pate and bread. But with the brightness of raspberry and the texture of coconut. This is a transition moment - allow it to simply happen."],
    ["Course 4 - Crab Omelette 2.0 «Jay Fai Tribute»","Этот курс - посвящение Джей Фай, одному из самых известных уличных поваров Бангкока. Огонь, скорость, контроль - переведённые здесь в более рафинированное выражение с крабом и икрой. Шардоне добавляет мягкую кремовость, которая отражает текстуру омлета и подчёркивает сладость краба.",
     "This dish is a tribute to Jay Fai - one of the most iconic street food chefs in Bangkok. Fire, speed, control - translated here into a more refined expression with crab and caviar. The Chardonnay brings a gentle creaminess that mirrors the texture of the omelette and enhances the sweetness of the crab."],
    ["Course 5 - Thai Ceviche (No Wine)","Самуи. Рифовые воды. Красный снаппер - выловлен именно здесь, поэтому текстура такая плотная и чистая. Идея этого курса - движение и яркость. Без вина - чтобы вы ощутили эту чистоту в полной мере.",
     "Samui. Reef waters. Red snapper - caught right here, so the texture is naturally firm and clean. The idea of this course is movement and brightness. We keep it without wine so you can experience that clarity fully."],
    ["Course 6 - Wagyu Tartare","Вагю в его самой чистой форме. Текстура невероятно мягкая - почти растворяется, создавая тихую, спокойную роскошь. Пино Нуар лёгкий и элегантный - он не конкурирует с блюдом. Просто поднимает его и сохраняет баланс.",
     "Here we move into wagyu in its most pure form. The texture is extremely soft - almost dissolving, creating a very quiet kind of richness. The Pinot Noir is light and elegant - it doesn't compete with the dish. It simply lifts it and keeps the balance."],
    ["Course 7 - Lobster Ravioli","Этот курс про контраст. Сладость лобстера против более тёмных, интенсивных нот рокфора. Шардоне имеет и структуру, и свежесть - оно соединяет эти два полюса и удерживает их в гармонии.",
     "This course is about contrast - the sweetness of lobster against the deeper, more intense notes of Roquefort. The Chardonnay has both structure and freshness, bridging these two elements and keeping them in harmony."],
    ["Course 8 - Chocolate & Raspberry (No Wine)","Небольшой ресет перед финальным курсом. Шоколад даёт интенсивность, малина разрезает её кислотностью, а тонка добавляет тепло и глубину.",
     "A small reset before the main course. Chocolate brings intensity, raspberry cuts through with acidity, and tonka adds warmth and depth."],
    ["Course 9 - Wagyu Truffle * MAIN","Кульминация вечера. Одно из самых культовых сочетаний в высокой кухне - вагю и трюфель. Речь о глубине, аромате и интенсивности. Кьянти добавляет структуру и пряность, которые поддерживают богатство и продлевают послевкусие.",
     "One of the most iconic combinations in fine dining - wagyu and truffle. It's about depth, aroma, and intensity. The Chianti adds structure and spice that support the richness and extend the flavor on the finish."],
    ["Course 10 - Honey Pear «Finale»","Мы подходим к финалу. Груша и ваниль - знакомые, деликатные. Трюфель добавляет неожиданную глубину. Мускат завершает опыт - цветочной сладостью и долгим послевкусием.",
     "We are approaching the finale. Pear and vanilla - familiar, delicate. Truffle adds an unexpected depth. The Muscat completes the experience with floral sweetness and a long finish."],
    {t:"GONG", h:80, label:"ГОНГ x2\nЗАВЕРШЕНИЕ\n20:55",
     ru:"[Официант и управляющий выходят к столу вместе.]\n\n[Официант берёт гонг. Взгляд на гостей.]\n\n[Первый удар.]\n\n[Пауза 2–3 секунды.]\n\n[Второй удар.]\n\n[Полная тишина. Управляющий делает шаг вперёд.]",
     en:"[Waiter and manager step forward together.]\n\n[Waiter takes the gong. Eye contact with guests.]\n\n[First strike.]\n\n[2–3 second pause.]\n\n[Second strike.]\n\n[Complete silence. Manager steps forward.]"},
    {t:"CLOSING", h:200, label:"ФИНАЛЬНОЕ\nСЛОВО\nУПРАВЛЯЮЩЕГО\n20:56\n~2–3 мин",
     ru:"Дорогие гости.\n\nВы только что прошли через всё то, что мы создавали месяцами.\n\nОт всей команды LUNA - шефа, официантов, кухни - спасибо, что пришли. Спасибо, что были здесь полностью.\n\nИ в знак нашей признательности - небольшой подарок. Это фирменный мерч LUNA. Что-то, что останется с вами после этого вечера.\n\n[Управляющий вручает мерч каждому гостю лично, с лёгким поклоном.]\n\nМы надеемся увидеть вас снова. Доброй ночи.",
     en:"Dear guests.\n\nYou have just experienced everything we spent months creating.\n\nFrom the entire LUNA team - the chef, the waiters, the kitchen - thank you for coming. Thank you for being fully present.\n\nAnd as a small token of our appreciation - a gift. This is LUNA's signature merch. Something to carry with you after this evening.\n\n[Manager presents merch to each guest personally, with a slight bow.]\n\nWe hope to see you again. Good night."},
  ];
}

// ─────────────────────────────────────────────────────────────────────────
//  SHARED: render scripts sheet
// ─────────────────────────────────────────────────────────────────────────
function renderScriptsSheet(ws, lang, title, sub) {
  ws.setColumnWidth(1,200); ws.setColumnWidth(2,lang==="both"?430:600); if(lang==="both") ws.setColumnWidth(3,400);
  const cols = lang==="both" ? 3 : 2;
  titleBlock(ws, cols, title, sub);

  ws.setRowHeight(4,32);
  const hdrs = lang==="both" ? [["A4","ЭТАП / КТО"],["B4","РЕПЛИКА (RU)"],["C4","SCRIPT (EN)"]] :
               lang==="ru"   ? [["A4","ЭТАП / КТО"],["B4","РЕПЛИКА"]] :
                               [["A4","STAGE / WHO"],["B4","SCRIPT"]];
  hdrs.forEach(([c,h])=>{ const r=ws.getRange(c); r.setValue(h); S(r,{bg:P.BK,fontColor:P.WH,bold:true,size:10,hAlign:"center",vAlign:"middle"}); B(r,P.BR); });

  const data = getScriptsData();
  let rn=5;
  data.forEach((s,si)=>{
    const isArr=Array.isArray(s), isObj=!isArr;
    const hgt=isObj?(s.h||90):90;
    ws.setRowHeight(rn,hgt);
    const bg=si%2===0?P.CR:P.C2;
    const isChef=isObj&&s.t==="CHEF", isWaiter=isObj&&s.t==="WAITER";
    const isGong=isObj&&s.t==="GONG", isClos=isObj&&s.t==="CLOSING";
    const lBg=isChef?P.CHEF_L:isGong?P.GONG_L:isClos?P.FIN_L:isWaiter?"FFF8EE":P.GL;
    const lFc=isChef?P.CHEF:isGong?P.GONG:isClos?P.FIN:isWaiter?P.WAITER:P.BK;
    const lBd=isChef?P.CHEF_BDR:isGong?P.GONG:isClos?"2C7A4E":P.BR;
    const lc=ws.getRange(rn,1); lc.setValue(isArr?s[0]:s.label);
    S(lc,{bg:lBg,fontColor:lFc,bold:true,size:9,hAlign:"center",vAlign:"middle",wrap:true}); B(lc,lBd,true);
    if(lang==="both") {
      const rc=ws.getRange(rn,2); rc.setValue(isArr?s[1]:s.ru);
      S(rc,{bg,fontColor:P.DK,italic:true,size:9,hAlign:"left",vAlign:"top",wrap:true}); B(rc,P.BR);
      const ec=ws.getRange(rn,3); ec.setValue(isArr?s[2]:s.en);
      S(ec,{bg,fontColor:P.MD,italic:true,size:9,hAlign:"left",vAlign:"top",wrap:true}); B(ec,P.BR);
    } else {
      const tc=ws.getRange(rn,2); tc.setValue(isArr?(lang==="ru"?s[1]:s[2]):(lang==="ru"?s.ru:s.en));
      S(tc,{bg,fontColor:P.DK,italic:true,size:9,hAlign:"left",vAlign:"top",wrap:true}); B(tc,P.BR);
    }
    rn++;
  });
  ws.setFrozenRows(4);
}

function buildScriptsRU(ss) {
  const ws=ss.insertSheet("SCRIPТЫ RU");
  renderScriptsSheet(ws,"ru","LUNA - СКРИПТЫ КУРСОВ (RU)","Реплики официанта и управляющего · Русский язык");
}
function buildScriptsEN(ss) {
  const ws=ss.insertSheet("SCRIPTS EN");
  renderScriptsSheet(ws,"en","LUNA - COURSE SCRIPTS (EN)","Waiter and manager scripts · English");
}

// ─────────────────────────────────────────────────────────────────────────
//  SHEET 4 · RUN SHEET EN
// ─────────────────────────────────────────────────────────────────────────
function buildRunSheetEN(ss) {
  const ws=ss.insertSheet("RUN SHEET EN");
  [200,80,100,320,90,200,110,115,90,80,60,260].forEach((w,i)=>ws.setColumnWidth(i+1,w));
  titleBlock(ws,12,"LUNA - GASTRO THEATER","SERVICE BIBLE v4  |  RUN SHEET (EN)  |  Up to 10 guests  |  MICHELIN FINE DINING");

  ws.setRowHeight(4,22);
  [["A4","Date:"],["B4","_______________"],["D4","Table:"],["E4","___"],
   ["G4","Guests:"],["H4","___"],["J4","Waiter:"],["K4","_______________"]].forEach(([c,v])=>{
    const r=ws.getRange(c); r.setValue(v); S(r,{fontColor:P.MD,bold:true,size:9,hAlign:"left",vAlign:"middle"});
  });
  ws.setRowHeight(5,5); ws.getRange("A5:L5").merge().setBackground("#"+P.GD);

  ws.setRowHeight(6,40);
  ["STAGE","TIME","WHO","ACTION / SCRIPT","DISH\nOUT","SHOW\nELEMENT","WINE\nPOUR","GUEST\nFEEDBACK","CLEAR","TIME\nEND","MIN","NOTES"].forEach((h,i)=>{
    const r=ws.getRange(6,i+1); r.setValue(h);
    S(r,{bg:P.BK,fontColor:P.WH,bold:true,size:9,hAlign:"center",vAlign:"middle",wrap:true}); B(r,P.BR);
  });

  const rows = [
    {t:"CHEF", d:["CHEF SPEECH\nOPENING","18:50","Chef",
      "18:50 - Chef approaches the table. Greets guests personally. Shares the story of LUNA, the concept of the set, his journey. Tone: personal, unhurried. ~10 minutes.",
      "","","","","","19:00","10","(!) Waiter stands nearby, does not interrupt. Background music continues."]},
    {t:"WAITER_BRIDGE", d:["WAITER\nBRIDGE","19:00","Waiter",
      "19:00 - Waiter steps forward. Brief close to the introduction (30–45 sec): introduces himself, announces the start of the set, leads into the gong.",
      "","","","","","19:01","1","Final line before the gong: 'Allow me to open the evening.'"]},
    {t:"GONG_OPEN", d:["GONG x1\nSET START","19:01","Waiter",
      "19:01 - One clean strike. 3–4 seconds of complete silence. Waiter returns gaze to guests. First course served.",
      "","GONG x1\nSTART","","","","19:02","1","(!) Silence after the strike is mandatory. Do not rush."]},
    {t:"COURSE", d:["COURSE 1\nYuzu Oyster","19:02","Waiter",
      "19:02 - Oyster, kimchi tomato, yuzu. Focus: texture, freshness, first impression.",
      "19:02","Ice presentation\n+ smoke element","19:03\nCava pour","19:05","19:09","19:10","8","Cava: Grifol Brut"]},
    {t:"COURSE", d:["COURSE 2\nTotoro Tuna\n«Purple Cloud»","19:12","Waiter",
      "19:13 - Tuna + caviar, purple cloud, mineral wine structure.",
      "19:14","«Cloud»\ndry ice","19:14\nWine pour","19:17","19:20","19:21","9","Wine: Le Vent Dans Les Voiles"]},
    {t:"TOWEL", d:[
      "HAND\nTOWEL","19:21","Waiter",
      "19:21 - Waiter presents a chilled scented hand towel to each guest individually. Courses 2, 4, 6 are eaten by hand - towel served once all guests have finished.",
      "","","","","","","","(!!) Mandatory. Present neatly, one by one to each guest."]},
    {t:"COURSE", d:["COURSE 3\nBread & Liver","19:23","Waiter",
      "19:24 - A classic reimagined. Pate, bread, raspberry, coconut. Intentional pause - no wine. Explain before serving.",
      "19:25","transition\nmoment","NO WINE","19:27","19:30","19:31","8","No wine - explain to guest before serving"]},
    {t:"COURSE", d:["COURSE 4\nCrab Omelette 2.0\n«Jay Fai Tribute»","19:33","Waiter",
      "19:34 - Fire, speed, control. Crab + caviar. Chardonnay mirrors texture, enhances sweetness.",
      "19:35","","19:35\nChardonnay","19:38","19:41","19:42","9","Wine: Little Things Chardonnay"]},
    {t:"TOWEL", d:[
      "HAND\nTOWEL","19:42","Waiter",
      "19:42 - Waiter presents a chilled scented hand towel to each guest individually. Courses 2, 4, 6 are eaten by hand - towel served once all guests have finished.",
      "","","","","","","","(!!) Mandatory. Present neatly, one by one to each guest."]},
    {t:"COURSE", d:["COURSE 5\nThai Ceviche\n(Red Snapper)","19:44","Waiter",
      "19:45 - Movement, brightness. Red snapper from Samui reef waters. No wine - experience the clarity fully.",
      "19:46","","NO WINE","19:48","19:51","19:52","8","No wine - explain to guest"]},
    {t:"COURSE", d:["COURSE 6\nWagyu Tartare","19:54","Waiter",
      "19:55 - Wagyu in its purest form. Quiet richness. Pinot Noir is elegant - lifts, does not compete.",
      "19:56","","19:56\nPinot Noir","19:59","20:03","20:04","10","Wine: Pinot Noir D'Doumah"]},
    {t:"TOWEL", d:[
      "HAND\nTOWEL","20:04","Waiter",
      "20:04 - Waiter presents a chilled scented hand towel to each guest individually. Courses 2, 4, 6 are eaten by hand - towel served once all guests have finished.",
      "","","","","","","","(!!) Mandatory. Present neatly, one by one to each guest."]},
    {t:"COURSE", d:["COURSE 7\nLobster Ravioli","20:06","Waiter",
      "20:07 - Contrast: sweetness of lobster vs. intensity of Roquefort. Chardonnay bridges both.",
      "20:08","Sauce finish\nat table","20:08\nChardonnay","20:11","20:15","20:16","10","Wine: Adelaide Hills Chardonnay"]},
    {t:"COURSE", d:["COURSE 8\nChocolate &\nRaspberry","20:18","Waiter",
      "20:19 - Small reset. Chocolate intensity, raspberry acidity, tonka warmth.",
      "20:20","","NO WINE","20:22","20:24","20:25","7","No wine - explain to guest"]},
    {t:"MAIN", d:["COURSE 9\nWagyu Truffle\n* MAIN","20:27","Waiter",
      "20:28 - The culmination. Wagyu + truffle. Chianti adds structure and spice. Slow down the pace.",
      "20:29","Truffle\ngrated tableside","20:29\nChianti","20:33","20:38","20:39","12","Wine: Fattoria Villa Saletta Chianti"]},
    {t:"COURSE", d:["COURSE 10\nHoney Pear\n«Finale»","20:41","Waiter",
      "20:42 - Pear + vanilla + unexpected truffle depth. Muscat closes with floral sweetness and long finish.",
      "20:43","Final candle\nat table","20:43\nMuscat","20:46","20:52","20:53","12","Wine: Muscat Beaumes de Venise"]},
    {t:"GONG_CLOSE", d:["GONG x2\nCLOSING","20:55","Waiter\n+ Manager",
      "20:55 - Waiter and manager approach together. First strike - 2–3 sec pause - second strike. Silence. Manager steps forward.",
      "","GONG x2\nFINALE","","","","20:56","1","(!) Full silence after second strike."]},
    {t:"CLOSING", d:["MANAGER\nFINALE","20:56","Manager",
      "20:56 - Final words (~2–3 min). Thanks guests. Presents LUNA merch to each guest personally.",
      "","LUNA merch\npersonal gift","","","","21:00","4","2–4 guests ~1 min. Up to 10 ~2.5 min."]},
  ];

  let ci2=0;
  rows.forEach((row,ri)=>{
    const sr=ri+7;
    const hMap={CHEF:80,WAITER_BRIDGE:50,GONG_OPEN:48,COURSE:60,MAIN:64,GONG_CLOSE:50,CLOSING:72,TOWEL:44};
    ws.setRowHeight(sr,hMap[row.t]||60);
    const even=ci2%2===0;
    if(row.t==="COURSE"||row.t==="MAIN") ci2++;
    const {t,d}=row;
    d.forEach((val,ci)=>{
      const cell=ws.getRange(sr,ci+1);
      cell.setValue(val); S(cell,{vAlign:"middle",wrap:true});
      const noW=String(val).includes("NO WINE");
      if(t==="CHEF"){
        S(cell,{bg:[P.CHEF_L,P.CHEF_L,"D6E4F0","EAF2FC",P.BK,P.BK,P.BK,P.BK,P.BK,P.CHEF_L,P.CHEF_L,"EAF2FC"][ci]||P.CR,fontColor:[P.CHEF,P.CHEF,P.CHEF,P.CHEF,P.BK,P.BK,P.BK,P.BK,P.BK,P.CHEF,P.CHEF,P.CHEF][ci]||P.MD,size:9,bold:ci<=1||ci===10,italic:ci===2,hAlign:ci===3||ci===11?"left":"center"});
        B(cell,P.CHEF_BDR,ci===0);
      } else if(t==="WAITER_BRIDGE"){
        S(cell,{bg:ci===3||ci===11?P.WAITER_L:"FFF8F0",fontColor:P.WAITER,size:9,bold:ci<=1||ci===10,italic:ci===2,hAlign:ci===3||ci===11?"left":"center"}); B(cell,"C8940A",ci===0);
      } else if(t==="GONG_OPEN"){
        S(cell,{bg:P.GONG_L,fontColor:ci===5||ci===0||ci===1||ci===10?P.GONG:P.MD,bold:ci<=1||ci===5||ci===10,size:9,hAlign:ci===3||ci===11?"left":"center"}); B(cell,P.GONG,ci===0||ci===5);
      } else if(t==="GONG_CLOSE"){
        S(cell,{bg:"F0FDF4",fontColor:ci===5||ci===0||ci===1||ci===10?P.FIN:P.MD,bold:ci<=1||ci===5||ci===10,size:9,hAlign:ci===3||ci===11?"left":"center"}); B(cell,"2C7A4E",ci===0||ci===5);
      } else if(t==="CLOSING"){
        S(cell,{bg:ci===5?"E8F5EE":"F0FDF4",fontColor:ci===5||ci===0||ci===1||ci===10?P.FIN:P.MD,bold:ci<=1||ci===5||ci===10,italic:ci===2,size:9,hAlign:ci===3||ci===11?"left":"center"}); B(cell,"2C7A4E",ci===0);
      } else if(t==="MAIN"){
        const b9=[P.GL,"FEF8F0","FFF5F0",P.CR,"F5FFFC","F0F4FF","FFFFF8",P.CR,P.CR,P.GL,P.BK,P.CR];
        const f9=["9A7420",P.RD,P.RD,P.DK,P.GR,P.NV,"9A7420",P.MD,P.MD,"9A7420",P.GD,P.MD];
        S(cell,{bg:b9[ci]||P.CR,fontColor:f9[ci]||P.MD,bold:ci<=1||ci===4||ci===10,italic:ci===2||ci===5,size:ci===10?11:9,hAlign:ci===3||ci===11?"left":"center"}); B(cell,P.BR,ci===0);
      } else {
        const bg=even?P.CR:P.C2;
        if(ci===0)      {S(cell,{bg:"F0E8D0",fontColor:P.BK,bold:true,size:9,hAlign:"center"});B(cell,P.BR,true);}
        else if(ci===1) {S(cell,{bg,fontColor:P.RD,bold:true,size:10,hAlign:"center"});B(cell,P.BR);}
        else if(ci===2) {S(cell,{bg:"FFF8EE",fontColor:P.WAITER,italic:true,size:8,hAlign:"center"});B(cell,P.BR);}
        else if(ci===3) {S(cell,{bg,fontColor:P.DK,size:8,hAlign:"left"});B(cell,P.BR);}
        else if(ci===4) {S(cell,{bg,fontColor:P.GR,bold:true,size:9,hAlign:"center"});B(cell,P.BR);}
        else if(ci===5) {S(cell,{bg:"F0F4FF",fontColor:P.NV,italic:true,size:8,hAlign:"left"});B(cell,P.BR);}
        else if(ci===6) {S(cell,{bg:"FFFFF8",fontColor:noW?"999999":P.BR,italic:noW,size:8,hAlign:"center"});B(cell,P.BR);}
        else if(ci===10){S(cell,{bg:P.BK,fontColor:P.GD,bold:true,size:10,hAlign:"center"});B(cell,P.BR);}
        else if(ci===11){S(cell,{bg,fontColor:P.MD,italic:true,size:8,hAlign:"left"});B(cell,P.BR);}
        else            {S(cell,{bg,fontColor:P.MD,size:8,hAlign:"center"});B(cell,P.BR);}
      }
    });
  });

  const tr=rows.length+7; ws.setRowHeight(tr,28);
  const tl=ws.getRange(tr,1,1,10); tl.merge();
  ws.getRange(tr,1).setValue("TOTAL  -  from chef's opening to merch presentation");
  S(tl,{bg:P.BK,fontColor:P.WH,bold:true,size:9,hAlign:"center",vAlign:"middle"}); B(tl,P.GD,true);
  const td=ws.getRange(tr,11); td.setValue("~130 min");
  S(td,{bg:P.BK,fontColor:P.GD,bold:true,size:10,hAlign:"center",vAlign:"middle"}); B(td,P.GD,true);
  const tt=ws.getRange(tr,12); tt.setValue("18:50 -> 21:00");
  S(tt,{bg:P.BK,fontColor:P.GL,size:9,hAlign:"center",vAlign:"middle"}); B(tt,P.GD,true);
  ws.setFrozenRows(6);
}

// ─────────────────────────────────────────────────────────────────────────
//  SHARED: sales scripts data
// ─────────────────────────────────────────────────────────────────────────
function getSalesData() {
  return {
    ru: [
      {tag:"ЭКСКЛЮЗИВНОСТЬ", tagBg:P.PUR_L, tagFc:P.PUR,
       text:"Прежде чем вы выберете из меню - хочу рассказать об одном варианте.\n\nУ нас есть гастрономический сет: десять курсов, выстроенных в определённой последовательности - от лёгкого к насыщенному, от морского к мясному. Устрица, тунец, лобстер, вагю с трюфелем.\n\nЭто не набор блюд - это один цельный ужин с логикой внутри.\n\nЭто уникальная возможность попробовать LUNA так, как мы её задумали.\n\nРассказать подробнее?"},
      {tag:"ЦЕННОСТЬ", tagBg:P.GRN_L, tagFc:P.GRN,
       text:"Прежде чем вы выберете из меню - хочу вам кое-что показать.\n\nУ нас есть гастрономический сет: десять курсов - устрица, тунец с икрой, лобстер, вагю с трюфелем, десерты. К сету можно добавить винное сопровождение отдельно.\n\nСтоимость сета - 4 900 бат на человека.\n\nЭто уникальная возможность: за ту цену, в которую обошлись бы три-четыре блюда à la carte, вы получаете полноценный ужин из десяти подач.\n\nХотите - покажу состав?"},
      {tag:"АВТОРСКИЙ СЕТ", tagBg:P.AMB_L, tagFc:P.AMB,
       text:"Могу предложить вам кое-что особенное.\n\nУ нас есть авторский гастрономический сет - десять курсов, каждый из которых шеф разрабатывал лично. Это его взгляд на азиатскую кухню через язык fine dining: нестандартные сочетания, своя логика подачи от начала до финала.\n\nЭто уникальная возможность - попасть на ужин, который шеф собрал как спектакль, а не просто как набор блюд.\n\nРассказать подробнее?"},
    ],
    en: [
      {tag:"EXCLUSIVITY", tagBg:P.PUR_L, tagFc:P.PUR,
       text:"Before you choose from the menu - I'd like to tell you about one option.\n\nWe have a gastronomic set: ten courses, built in a specific sequence - from light to rich, from seafood to meat. Oyster, tuna, lobster, wagyu with truffle.\n\nThis is not a selection of dishes - it's one complete dinner with a logic inside.\n\nThis is a unique opportunity to experience LUNA the way we intended it.\n\nShall I tell you more?"},
      {tag:"VALUE", tagBg:P.GRN_L, tagFc:P.GRN,
       text:"Before you choose from the menu - I'd like to show you something.\n\nWe have a gastronomic set: ten courses - oyster, tuna with caviar, lobster, wagyu with truffle, desserts. Wine pairing is available separately.\n\nThe set is 4,900 baht per person.\n\nThis is a unique opportunity: for the price of three or four a la carte dishes, you get a complete dinner of ten courses.\n\nWould you like to see the full menu?"},
      {tag:"CHEF'S SET", tagBg:P.AMB_L, tagFc:P.AMB,
       text:"May I offer you something special.\n\nWe have a chef's gastronomic set - ten courses, each developed personally by our chef. It's his vision of Asian cuisine through the language of fine dining: unexpected combinations, a clear logic from start to finish.\n\nThis is a unique opportunity - a dinner the chef built as a performance, not just a selection of dishes.\n\nShall I tell you more?"},
    ]
  };
}

// ─────────────────────────────────────────────────────────────────────────
//  SHEET 5 · SALES RU
// ─────────────────────────────────────────────────────────────────────────
function buildSalesRU(ss) {
  const ws=ss.insertSheet("SALES RU");
  ws.setColumnWidth(1,160); ws.setColumnWidth(2,560);
  titleBlock(ws,2,"LUNA - СКРИПТЫ ПРОДАЖИ СЕТА","Три варианта для официанта · Русский язык · Гость пришёл на а-ля карт");

  ws.setRowHeight(4,32);
  [["A4","АКЦЕНТ"],["B4","ТЕКСТ ОФИЦИАНТА"]].forEach(([c,h])=>{
    const r=ws.getRange(c); r.setValue(h);
    S(r,{bg:P.BK,fontColor:P.WH,bold:true,size:10,hAlign:"center",vAlign:"middle"}); B(r,P.BR);
  });

  const data=getSalesData().ru;
  data.forEach((s,i)=>{
    const r=i+5; ws.setRowHeight(r,140);
    const bg=i%2===0?P.CR:P.C2;
    const tag=ws.getRange(r,1); tag.setValue(s.tag);
    S(tag,{bg:s.tagBg,fontColor:s.tagFc,bold:true,size:10,hAlign:"center",vAlign:"middle",wrap:true}); B(tag,P.BR,true);
    const txt=ws.getRange(r,2); txt.setValue(s.text);
    S(txt,{bg,fontColor:P.DK,size:10,hAlign:"left",vAlign:"top",wrap:true}); B(txt,P.BR);
  });
  ws.setFrozenRows(4);
}

// ─────────────────────────────────────────────────────────────────────────
//  SHEET 6 · SALES EN
// ─────────────────────────────────────────────────────────────────────────
function buildSalesEN(ss) {
  const ws=ss.insertSheet("SALES EN");
  ws.setColumnWidth(1,160); ws.setColumnWidth(2,560);
  titleBlock(ws,2,"LUNA - SET MENU SALES SCRIPTS","Three approaches for the waiter · English · Guest arrived for a la carte");

  ws.setRowHeight(4,32);
  [["A4","APPROACH"],["B4","WAITER SCRIPT"]].forEach(([c,h])=>{
    const r=ws.getRange(c); r.setValue(h);
    S(r,{bg:P.BK,fontColor:P.WH,bold:true,size:10,hAlign:"center",vAlign:"middle"}); B(r,P.BR);
  });

  const data=getSalesData().en;
  data.forEach((s,i)=>{
    const r=i+5; ws.setRowHeight(r,140);
    const bg=i%2===0?P.CR:P.C2;
    const tag=ws.getRange(r,1); tag.setValue(s.tag);
    S(tag,{bg:s.tagBg,fontColor:s.tagFc,bold:true,size:10,hAlign:"center",vAlign:"middle",wrap:true}); B(tag,P.BR,true);
    const txt=ws.getRange(r,2); txt.setValue(s.text);
    S(txt,{bg,fontColor:P.DK,size:10,hAlign:"left",vAlign:"top",wrap:true}); B(txt,P.BR);
  });
  ws.setFrozenRows(4);
}

// ─────────────────────────────────────────────────────────────────────────
//  SHEET 7 · SALES PRINT
// ─────────────────────────────────────────────────────────────────────────
function buildSalesPrint(ss) {
  const ws=ss.insertSheet("SALES PRINT");

  // Page setup for A4 print
  ws.setColumnWidth(1,30);
  ws.setColumnWidth(2,340);
  ws.setColumnWidth(3,30);
  ws.setColumnWidth(4,340);
  ws.setColumnWidth(5,30);

  // Print settings
  const ps=ws.getPageSetup ? ws.getPageSetup() : null;

  // ── TOP HEADER ──
  ws.setRowHeight(1,50);
  const hdr=ws.getRange("A1:E1"); hdr.merge();
  ws.getRange("A1").setValue("LUNA  -  СКРИПТЫ ПРОДАЖИ СЕТА  /  SET MENU SALES SCRIPTS");
  S(hdr,{bg:P.BK,fontColor:P.GD,bold:true,size:14,hAlign:"center",vAlign:"middle"});
  ws.setRowHeight(2,14);
  const sub=ws.getRange("A2:E2"); sub.merge();
  ws.getRange("A2").setValue("Для официанта · For the waiter · 3 варианта RU + 3 variants EN · Распечатать и раздать");
  S(sub,{bg:P.BK,fontColor:P.GL,italic:true,size:9,hAlign:"center",vAlign:"middle"});
  ws.setRowHeight(3,6);
  ws.getRange("A3:E3").merge().setBackground("#"+P.GD);
  ws.setRowHeight(4,16);

  // ── COLUMN LABELS ──
  ws.setRowHeight(5,28);
  const lblRU=ws.getRange("B5"); lblRU.setValue("РУССКИЙ ЯЗЫК");
  S(lblRU,{bg:P.PUR_L,fontColor:P.PUR,bold:true,size:11,hAlign:"center",vAlign:"middle"});
  B(lblRU,P.PUR);
  const lblEN=ws.getRange("D5"); lblEN.setValue("ENGLISH");
  S(lblEN,{bg:P.AMB_L,fontColor:P.AMB,bold:true,size:11,hAlign:"center",vAlign:"middle"});
  B(lblEN,"B8922E");

  ws.setRowHeight(6,10);

  const salesRU=getSalesData().ru;
  const salesEN=getSalesData().en;

  // tag colors per card
  const tagColors=[
    {bg:P.PUR_L,fc:P.PUR},
    {bg:P.GRN_L,fc:P.GRN},
    {bg:P.AMB_L,fc:P.AMB},
  ];

  // Render cards: each card = 3 rows: tag header, text body, spacer
  salesRU.forEach((sru,i)=>{
    const sen=salesEN[i];
    const tagRow=7+i*4;
    const txtRow=tagRow+1;
    const sepRow=tagRow+2;
    const spc2Row=tagRow+3;

    ws.setRowHeight(tagRow,28);
    ws.setRowHeight(txtRow,150);
    ws.setRowHeight(sepRow,2);
    ws.setRowHeight(spc2Row,14);

    // RU tag
    const ruTag=ws.getRange(tagRow,2);
    ruTag.setValue(sru.tag);
    S(ruTag,{bg:tagColors[i].bg,fontColor:tagColors[i].fc,bold:true,size:10,hAlign:"center",vAlign:"middle"});
    B(ruTag,tagColors[i].fc.replace && tagColors[i].fc,true);
    ruTag.setBorder(true,true,false,true,false,false,"#"+tagColors[i].fc,SpreadsheetApp.BorderStyle.SOLID_MEDIUM);

    // RU text
    const ruTxt=ws.getRange(txtRow,2);
    ruTxt.setValue(sru.text);
    S(ruTxt,{bg:P.WH,fontColor:P.DK,size:9,hAlign:"left",vAlign:"top",wrap:true});
    ruTxt.setBorder(false,true,true,true,false,false,"#"+tagColors[i].fc,SpreadsheetApp.BorderStyle.SOLID_MEDIUM);

    // EN tag
    const enTag=ws.getRange(tagRow,4);
    enTag.setValue(sen.tag);
    S(enTag,{bg:tagColors[i].bg,fontColor:tagColors[i].fc,bold:true,size:10,hAlign:"center",vAlign:"middle"});
    enTag.setBorder(true,true,false,true,false,false,"#"+tagColors[i].fc,SpreadsheetApp.BorderStyle.SOLID_MEDIUM);

    // EN text
    const enTxt=ws.getRange(txtRow,4);
    enTxt.setValue(sen.text);
    S(enTxt,{bg:P.WH,fontColor:P.DK,size:9,hAlign:"left",vAlign:"top",wrap:true});
    enTxt.setBorder(false,true,true,true,false,false,"#"+tagColors[i].fc,SpreadsheetApp.BorderStyle.SOLID_MEDIUM);

    // Divider line
    ws.getRange(sepRow,2,1,3).merge().setBackground("#"+P.GD);
  });

  // ── FOOTER ──
  const lastRow=7+salesRU.length*4;
  ws.setRowHeight(lastRow,30);
  const foot=ws.getRange(lastRow,1,1,5); foot.merge();
  ws.getRange(lastRow,1).setValue("LUNA Gastro Theater  |  Koh Samui  |  «Это уникальная возможность»  |  «This is a unique opportunity»");
  S(foot,{bg:P.BK,fontColor:P.GD,italic:true,size:9,hAlign:"center",vAlign:"middle"});

  ws.setFrozenRows(0);
}
