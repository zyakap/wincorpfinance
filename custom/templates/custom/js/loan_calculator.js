

<script>
    
     $(function(){

        $('.rangeslider').on('change', function() {
          
            const amtslide = $('#amt').val();
            const dysld = $('#dys').val();

            const amount = parseInt(amtslide)
            const selected_fns = parseInt(dysld)

            const amount_display = parseInt(amtslide).toLocaleString('en-US', {maximumFractionDigits:2})

            // Original Calcs for slider
                //const annual_interest_input = $('#interestrate').text();
                //const parsedAI = parseFloat(annual_interest_input)
                // console.log('parsed interest:' + annual_interest)
                //const r_by_n = parsedAI
                //console.log(parsedAI)
                //const term = selected_fns / 26
                //const r_by_n_plus_1 = r_by_n + 1
                //const nt = -26 * term
                //const exp = r_by_n_plus_1 ** nt
                //const denominator = 1 - exp
                //const pmt = amount * (r_by_n / denominator)
            
            // Custom HoriVert
                //const interest_rate = (selected_fns * 0.01) - 0.03 + 0.15
                //const pmt = ((interest_rate * amount) + amount + 50)/selected_fns


            // Custom KTP FINANCE
            // Repayment table data
            const repaymentTable = {
                200: [130, 93, 70, 60, 50, 43, 38, 33, 30],
                300: [195, 140, 105, 90, 75, 64, 56, 50, 45],
                400: [260, 187, 140, 120, 100, 86, 75, 67, 60],
                500: [325, 233, 175, 150, 125, 107, 94, 83, 75],
                600: [390, 280, 210, 180, 150, 129, 113, 100, 90],
                700: [455, 327, 245, 210, 175, 150, 131, 117, 105],
                800: [520, 373, 280, 240, 200, 171, 150, 133, 120],
                900: [585, 420, 315, 270, 225, 193, 169, 150, 135],
                1000: [650, 467, 350, 300, 250, 214, 188, 167, 150],
                1100: [715, 513, 385, 330, 275, 236, 206, 183, 165],
                1200: [780, 560, 420, 360, 300, 257, 225, 200, 180],
                1300: [845, 607, 455, 390, 325, 279, 244, 217, 195],
                1400: [910, 653, 490, 420, 350, 300, 263, 233, 210],
                1500: [975, 700, 525, 450, 375, 321, 281, 250, 225],
                1600: [1040, 747, 560, 480, 400, 343, 300, 267, 240],
                1700: [1105, 793, 595, 510, 425, 364, 319, 283, 255],
                1800: [1170, 840, 630, 540, 450, 386, 338, 300, 270],
                1900: [1235, 887, 665, 570, 475, 407, 356, 317, 285],
                2000: [1300, 933, 700, 600, 500, 429, 375, 333, 300],
                2100: [1365, 980, 735, 630, 525, 450, 394, 350, 315],
                2200: [1430, 1027, 770, 660, 550, 471, 413, 367, 335],
                2300: [1495, 1073, 805, 690, 575, 493, 431, 383, 355],
                2400: [1560, 1120, 840, 720, 600, 514, 450, 400, 375],
                2500: [1625, 1167, 875, 750, 625, 536, 469, 417, 395],
                2600: [1690, 1213, 910, 780, 650, 557, 488, 433, 390],
                2700: [1755, 1260, 945, 810, 675, 579, 506, 450, 405],
                2800: [1820, 1307, 980, 840, 700, 600, 525, 467, 420],
                2900: [1885, 1353, 1015, 870, 725, 621, 544, 483, 435],
                3000: [1950, 1400, 1050, 900, 750, 643, 563, 500, 455],
                3100: [2015, 1447, 1085, 930, 775, 664, 581, 517, 470],
                3200: [2080, 1493, 1120, 960, 800, 685, 600, 533, 485],
                3300: [2145, 1540, 1155, 990, 825, 707, 619, 550, 495],
                3400: [2210, 1587, 1190, 1020, 850, 729, 638, 567, 510],
                3500: [2275, 1633, 1225, 1050, 875, 750, 656, 583, 525],
                3600: [2340, 1680, 1260, 1080, 900, 771, 675, 600, 540],
                3700: [2405, 1727, 1295, 1110, 925, 793, 694, 617, 555],
                3800: [2470, 1773, 1330, 1140, 950, 814, 713, 633, 570],
                3900: [2535, 1820, 1365, 1170, 975, 836, 731, 650, 585],
                4000: [2600, 1867, 1400, 1200, 1000, 857, 750, 667, 600],
                4100: [2665, 1913, 1435, 1230, 1025, 879, 769, 683, 615],
                4200: [2730, 1960, 1470, 1260, 1050, 900, 788, 700, 630],
                4300: [2795, 2007, 1505, 1290, 1075, 921, 806, 717, 645],
                4400: [2860, 2053, 1540, 1320, 1100, 943, 825, 733, 660],
                4500: [2925, 2100, 1575, 1350, 1125, 964, 844, 750, 675],
                4600: [2990, 2147, 1610, 1380, 1150, 985, 863, 767, 690],
                4700: [3055, 2193, 1645, 1410, 1175, 1007, 881, 783, 705],
                4800: [3120, 2240, 1680, 1440, 1200, 1029, 900, 800, 720],
                4900: [3185, 2287, 1715, 1470, 1225, 1050, 919, 817, 735],
                5000: [3250, 2333, 1750, 1500, 1250, 1071, 938, 833, 750]
            };

            // Function to get the payment for the selected amount and fortnights
            function getPayment(amount, num_fns) {
                if (!repaymentTable.hasOwnProperty(amount)) {
                    return "Invalid loan amount";
                }
                
                const maxFn = repaymentTable[amount].length;
                if (num_fns < 1 || num_fns > maxFn) {
                    return " - Reduce # of fortnights";
                }
                
                return repaymentTable[amount][num_fns - 1];
            }

            //ktp finance
            // Get the payment for the selected amount and fortnights
            const pmt = getPayment(amount, selected_fns);
            
            // Calculation Flow  - do not modify
            const loan_amount_with_interests = pmt * selected_fns

            const totalpayint = loan_amount_with_interests 
            const calculated_interest = loan_amount_with_interests - amount

            const interest = calculated_interest.toLocaleString('en-US', {maximumFractionDigits:2})
            const total_payable = pmt.toLocaleString('en-US', {maximumFractionDigits:2})

            const loan_limit = $('#loanlimit').text()
            const ll = parseInt(loan_limit)
            
            if (pmt > ll ) {
                console.log(ll)
                $('#totalcalc').css('color','orange');
                $('#totwarn').css('color','red').show().text('Exceeds your loan limit. Application will be automatically rejected by the system.');
                $('#applybtn_note').css('color','red').show().text('Application will be automatically rejected by the system.');
                
            } else {
                console.log(ll)
                $('#totalcalc').css('color','white');
                $('#totwarn').css('color','green').show().text('Loan is within limits.');
                $('#applybtn_note').css('color','red').hide();
                
            }

            $('#amountinfo').text('K' + amount_display);
            $('#amtname').val(parseInt(amtslide));
            $('#daysinfo').text(parseInt(dysld) + ' fortnights');
            $('#dayname').val(parseInt(dysld));
            $('#interestcalc').text('K' + interest);
            $('#totalcalc').text('K' + total_payable);
        });

        $('#amtname').on("click", function() {
            $('#applybtn_note').hide();
        });
        $('#dayname').on("click", function() {
            $('#applybtn_note').hide();
        });
 
        var $element = $('input[type="range"]');

        $element
        .rangeslider({
            polyfill: false,
            onInit: function() {
            var $handle = $('.rangeslider__handle', this.$range);
            updateHandle($handle[0], this.value);
            }
        })
        .on('input', function(e) {
            var $handle = $('.rangeslider__handle', e.target.nextSibling);
            updateHandle($handle[0], this.value);
        });

        function updateHandle(el, val) {
        el.textContent = val;
        }
   
    });

</script>