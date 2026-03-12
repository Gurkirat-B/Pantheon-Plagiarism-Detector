// If-Else Statement Example - Converted from switch
#include <iostream>
using namespace std;

string getDayName(int day) {
    string name;
    
    if(day == 1) {
        name = "Monday";
    }
    else if(day == 2) {
        name = "Tuesday";
    }
    else if(day == 3) {
        name = "Wednesday";
    }
    else if(day == 4) {
        name = "Thursday";
    }
    else if(day == 5) {
        name = "Friday";
    }
    else if(day == 6) {
        name = "Saturday";
    }
    else if(day == 7) {
        name = "Sunday";
    }
    else {
        name = "Invalid day";
    }
    
    return name;
}

int main() {
    for(int i = 1; i <= 7; i++) {
        cout << "Day " << i << " is " << getDayName(i) << endl;
    }
    return 0;
}
